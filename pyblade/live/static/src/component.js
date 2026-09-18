import { Directives } from './directives.js';
import { Idiomorph } from "../vendor/idiomorph.esm.js"
import { applyKeys, morphCallbacks } from './morph.js';
import { readLines } from './streaming.js';
import { showErrorPage } from './errors.js';
import { addPushes, runScripts } from './stacks.js';
import { pbFor, runComponentScripts } from './script.js';

/**
 * How many times a request refused for asking too often is sent again, having
 * waited as long as it was told to, before the component gives up on it. Enough
 * for a burst of clicks to get through; not so many that a server refusing for
 * good is asked for ever.
 */
const RETRIES_WHEN_THROTTLED = 3;

export class Component {
    constructor(id, element, snapshot, store) {
        this.id = id;
        this.element = element;
        this.store = store;

        // Store snapshot directly in JS Memory
        this.store.set(this.id, snapshot);

        // Callback registries for directives. Sets, because a directive gives up
        // its callbacks when its binding is dropped, and an update drops as many
        // bindings as it renews.
        this.loadingStartCallbacks = new Set();
        this.loadingEndCallbacks = new Set();
        this.dirtyChangeCallbacks = new Set();
        this.stateChangeCallbacks = new Set();
        this.streamUpdateCallbacks = new Set();
        this.destroyCallbacks = new Set();

        // Directive bindings, kept per element so that an update only binds
        // what morphing has actually added or changed
        this._bindings = new Map();

        // Form state registry (react-hook-form inspired)
        this.formState = {
            values: { ...snapshot.state },
            dirtyFields: new Set(),
            touchedFields: new Set(),
        };
        this.pendingUpdates = null;
        this.pendingUpdateTimer = null;

        // What is waiting to be asked of the server, so that one request goes
        // out at a time and each carries what the last answer brought back
        this._queue = null;

        // The dirty properties as they were last told, so that they are only
        // told again when they have actually changed
        this._dirtySignature = '';

        // Requests are numbered as they are made, and answers applied in that
        // order rather than in the order they happen to come back. A slow
        // answer landing after a quick one would otherwise take the page back
        // to an older state -- and, worse, that older state is what the next
        // request would then be built on.
        this._asked = 0;
        this._applied = 0;

        // What is listening for a request that came back wrong
        this.errorCallbacks = new Set();

        // Bind directives to DOM
        Directives.apply(this.element, this);

        // What the component wrote @script, now that there is a component to
        // hand it
        runComponentScripts(this);
    }

    /** The component as its @script blocks, and any other JavaScript, see it. */
    get $pb() {
        return (this._pb ??= pbFor(this));
    }

    async callServerMethod(methodName, params = [], options = undefined) {
        await this.sendRequest({ action: methodName, params, ...(options || {}) });
    }

    async setProperties(updatedProperties, delay = 300) {
        const [propName, value] = updatedProperties;
        
        // Update local form state immediately (react-hook-form pattern)
        this.formState.values[propName] = value;
        this.formState.touchedFields.add(propName);
        this.refreshDirty();
        
        // Batch updates - don't send immediately
        this.pendingUpdates = this.pendingUpdates || {};
        this.pendingUpdates[propName] = value;
        
        // Clear existing timer and set new one for batched update
        if (this.pendingUpdateTimer) {
            clearTimeout(this.pendingUpdateTimer);
        }
        
        this.pendingUpdateTimer = setTimeout(async () => {
            if (this.pendingUpdates) {
                const updates = Object.entries(this.pendingUpdates).flat();
                this.pendingUpdates = null;
                await this.sendRequest({ action: "$set", params: updates });
            }
        }, delay);
    }

    /**
     * Ask the server something, once whatever was asked before has been answered.
     *
     * A request carries the state the component last heard about, so two of them
     * sent together both carry the older one: the second answer is worked out
     * from the same state as the first and lands on top of it, and what the
     * first did is lost. Clicking twice quickly counted once.
     *
     * So they queue. The next goes out when the last has answered, by which time
     * the state it carries is the state that answer brought back.
     */
    sendRequest(payload) {
        const waitingOn = this._queue;

        // Whoever is last in the queue holds it until they have been answered
        let answered;
        const place = new Promise((resolve) => { answered = resolve; });
        this._queue = place;

        // With nothing in flight there is nothing to wait for, and a request
        // held back even a tick is an interaction that felt slower than it was
        const sending = waitingOn
            ? waitingOn.then(() => this._send(payload))
            : this._send(payload);

        const done = () => {
            // Nobody queued behind us, so the queue is empty again
            if (this._queue === place) this._queue = null;
            answered();
        };

        sending.then(done, done);

        return sending;
    }

    async _send(payload, attempt = 0) {
        // Told to wait by the server: a request sent now would only be refused
        // again, and would count against us while it was
        const wait = this.quietFor();
        if (wait > 0) await new Promise(resolve => setTimeout(resolve, wait));

        const csrfToken = document.querySelector('script[data-csrf]')?.getAttribute('data-csrf');

        // What is being asked of the server, so that an element watching one
        // action or one property can tell whether this is the one
        this.loadingStartCallbacks.forEach(cb => cb(payload));

        const ticket = ++this._asked;

        try {
            let response;

            try {
                response = await fetch('/pyblade/live/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify({
                        id: this.id,
                        snapshot: this.store.get(this.id),
                        // What the page already holds, so that a component written
                        // inside this one is left where it is rather than started over
                        known: [...window.PyBlade.components.keys()],
                        // What was typed into the form and not sent yet, so that
                        // the action runs against the form as the reader left it
                        updates: this.pendingUpdatesToSend(payload),
                        ...payload
                    })
                });
            } catch (error) {
                // Nothing came back at all: the connection, not the server
                return this.failed({ status: 0, payload, error });
            }

            if (!response.ok) {
                // Refused for asking too often. The server refuses before the
                // action runs, so nothing was done and asking again cannot do it
                // twice: the request waits out what it was told and goes again,
                // rather than a click being lost for having been quick.
                if (response.status === 429) {
                    this.keepQuiet(response.headers.get('Retry-After'));

                    if (attempt < RETRIES_WHEN_THROTTLED) return await this._send(payload, attempt + 1);
                }

                // While developing, a refusal comes back with the PyBlade error
                // page in it, which is worth far more than the status alone
                return this.failed({
                    status: response.status,
                    payload,
                    answer: await this.readAnswer(response),
                });
            }

            // An action that answers as it goes says so with its content type:
            // its answer is a line of JSON at a time, the last of which is the
            // answer proper and the rest what it streamed on the way there.
            if (response.headers.get('Content-Type')?.includes('x-ndjson')) {
                await readLines(response.body, (line) => {
                    if (line.stream) return this.streamTo(line.stream);

                    // An action that went wrong half way through cannot answer
                    // with a status any more: it says so in its last line, and
                    // that line is a failure rather than a new state to apply
                    if (line.error) return this.failed({ status: 500, payload, answer: line });

                    this.apply(ticket, line);
                });
                return;
            }

            const data = await response.json();
            if (data) this.apply(ticket, data);
        } finally {
            this.loadingEndCallbacks.forEach(cb => cb(payload));
        }
    }

    /**
     * Apply an answer, unless a newer one has already been applied.
     *
     * Two requests going at once come back in whatever order the network and
     * the server between them decide. The older answer is not merely out of
     * date: the state it carries would become what the next request is built
     * on, so applying it loses everything the newer one said.
     */
    apply(ticket, data) {
        if (ticket < this._applied) return;

        this._applied = ticket;
        this.update(data);
    }

    /**
     * Say that a request came back wrong, rather than leaving the page as one
     * that has quietly stopped working.
     *
     * Nothing of the answer is applied: a component whose request was refused
     * holds what it held before, and the page is told so it can say something.
     *
     *     document.addEventListener('live:error', ({ detail }) => {
     *         banner.textContent = detail.expired
     *             ? 'Your session has ended. Reload the page to carry on.'
     *             : 'Something went wrong. Try again.';
     *     });
     */
    /**
     * Stop asking for as long as the server said to.
     *
     * Refused for asking too often, the page keeps quiet rather than asking
     * again at once: every request sent meanwhile would be refused too, and
     * would count against it while it was.
     */
    keepQuiet(retryAfter) {
        const seconds = Number.parseInt(retryAfter, 10);
        const until = Date.now() + (Number.isFinite(seconds) && seconds > 0 ? seconds : 1) * 1000;

        this._quietUntil = Math.max(this._quietUntil || 0, until);
    }

    /** How many milliseconds are left before the component may ask again. */
    quietFor() {
        return Math.max(0, (this._quietUntil || 0) - Date.now());
    }

    failed({ status, payload, error = null, answer = null }) {
        const detail = {
            id: this.id,
            action: payload?.action ?? null,
            status,

            // A session or a token that has gone stale is refused, and asking
            // again will be refused too until the page has been loaded afresh
            expired: status === 403,

            // Refused for asking too often, and how long before asking again
            throttled: status === 429,
            retryIn: status === 429 ? this.quietFor() : 0,
            error,
            message: answer?.error ?? null,

            // The PyBlade error page, which the server sends while developing
            // and never in production
            page: answer?.page ?? null,
        };

        console.error(
            `PyBlade: ${detail.action || 'a request'} for ${this.id} was not answered `
            + `(${status || 'no answer at all'}).`,
            detail.message || ''
        );

        // Said first, then shown: whatever the page makes of an error, it hears
        // about it even if there is nowhere to show the error page
        this.errorCallbacks.forEach(cb => cb(detail));
        document.dispatchEvent(new CustomEvent('live:error', { detail, cancelable: true }));

        if (detail.page) showErrorPage(detail.page);
    }

    /** What a refusal holds, where it holds anything a page can read. */
    async readAnswer(response) {
        try {
            return await response.json();
        } catch {
            return null;
        }
    }

    /** Watch for a request of this component's that came back wrong. */
    onError(callback, signal) {
        return this._register(this.errorCallbacks, callback, signal);
    }

    update({ html, snapshot, events = [], streams = [], pushes = [], query = null, scroll = null, redirect = null }) {
        this.store.set(this.id, snapshot);

        // What the new markup pushed and the page does not hold yet -- a script
        // it needs -- goes in first, so that it is there when the markup is
        runScripts(addPushes(pushes));

        // What has not been typed into is the server's to say, so that the
        // page keeps up with a property an action changed
        Object.entries(snapshot?.state || {}).forEach(([name, value]) => {
            if (!this.formState.touchedFields.has(name)) this.formState.values[name] = value;
        });

        // A renderless action answers with its new state and no HTML at all,
        // and the page is left as it is
        if (html) {
            // A component written inside this one answers for itself: its
            // element is left as it is, with the state, the listeners and the
            // timers it has been keeping. pb:ignore, pb:replace and pb:key are
            // read by the same callbacks.
            applyKeys(this.element);

            Idiomorph.morph(this.element, applyKeys(this.incoming(html)), {
                callbacks: morphCallbacks({ isOwn: (node) => !this.isNested(node) }),
            });

            Directives.apply(this.element, this);

            // A @script the new markup brought that has not run yet: one inside
            // an @if that has just come true
            runComponentScripts(this);

            // Whatever the new markup brought with it, and whatever it took away
            window.PyBlade.scan(this.element);
            window.PyBlade.prune();
        }

        // Handed to the core rather than raised here: an event is for the other
        // components on the page as much as for whatever JavaScript listens.
        events.forEach(event => window.PyBlade.deliver(event, this.id));

        // What the action streamed while there was nowhere to stream it to:
        // written now, all at once, rather than as it was written
        streams.forEach(chunk => this.streamTo(chunk));

        // Which page of a paginated list is being looked at, so that the
        // address bar says it and reloading the page comes back to it
        if (query) this.writeQuery(query);
        if (html && scroll !== null) this.scrollAfterUpdate(scroll);

        // What the server has answered for is no longer dirty
        this.refreshDirty();

        // Trigger state change callbacks
        this.stateChangeCallbacks.forEach(cb => cb());

        if (redirect) {
            redirect.navigate ? this.navigate(redirect.href) : (window.location.href = redirect.href);
        }
    }

    // Callback registration methods for directives.
    //
    // A directive passes the signal of its binding along: the callback is then
    // forgotten as soon as that binding is renewed or dropped, instead of
    // piling up on every update and running against elements long gone.
    _register(registry, callback, signal) {
        if (signal?.aborted) return () => {};

        registry.add(callback);

        const forget = () => registry.delete(callback);
        signal?.addEventListener('abort', forget, { once: true });

        return forget;
    }

    onLoadingStart(callback, signal) {
        return this._register(this.loadingStartCallbacks, callback, signal);
    }

    onLoadingEnd(callback, signal) {
        return this._register(this.loadingEndCallbacks, callback, signal);
    }

    /**
     * Watch which properties have been changed here and not yet sent.
     *
     * The callback is handed the names of them, every time that set changes:
     * an element watching one of its own decides for itself what to do about it.
     */
    onDirtyChange(callback, signal) {
        return this._register(this.dirtyChangeCallbacks, callback, signal);
    }

    onStateChange(callback, signal) {
        return this._register(this.stateChangeCallbacks, callback, signal);
    }

    onStreamUpdate(callback, signal) {
        return this._register(this.streamUpdateCallbacks, callback, signal);
    }

    onDestroy(callback, signal) {
        return this._register(this.destroyCallbacks, callback, signal);
    }

    /**
     * Whether a node belongs to a component written inside this one.
     *
     * The root of this component carries an id too, and that one is ours.
     */
    isNested(node) {
        return node !== this.element && node.nodeType === 1 && node.hasAttribute('pb:id');
    }

    /**
     * The answer of the server, as an element, ready to be morphed in.
     *
     * Put back into it are the components this one only said the place of.
     *
     * A component already on the page is not rendered again: its parent answers
     * with an empty element carrying its id. Morphing pairs the old markup with
     * the new by what the two look like, so the placeholder is filled with what
     * the page holds before it is handed over -- an empty element of another
     * name would be taken for a different one and the component swept away with it.
     */
    incoming(html) {
        const incoming = document.createElement('div');
        incoming.innerHTML = html;

        incoming.querySelectorAll('[pb\\:placeholder]').forEach((placeholder) => {
            const id = placeholder.getAttribute('pb:id');
            const live = document.querySelector(`[pb\\:id="${CSS.escape(id)}"]`);

            if (live) placeholder.replaceWith(live.cloneNode(true));
        });

        // The root of the answer is the component itself, which is what the
        // element being morphed is to be brought up to
        return incoming.firstElementChild || incoming;
    }

    /**
     * What the reader has put into a field, kept on the page.
     *
     * Whether it is sent now or with whatever the component asks next, this is
     * where it is held meanwhile, and what makes the property dirty.
     */
    setLocal(name, value) {
        this.formState.values[name] = value;
        this.formState.touchedFields.add(name);
        this.refreshDirty();
    }

    /**
     * What the server says a property holds, for a field that has not been
     * typed into. A field the reader is working in is left with what they typed.
     */
    seedLocal(name, value) {
        if (this.formState.touchedFields.has(name)) return;

        this.formState.values[name] = value;
    }

    /**
     * What the page holds and the server has not seen, to travel with a request.
     *
     * A field written pb:model says nothing on its own: this is how what was
     * typed into it reaches the server, with whatever the component asks next.
     */
    pendingUpdatesToSend(payload = {}) {
        const updates = {};

        this.dirtyFields().forEach((name) => { updates[name] = this.formState.values[name]; });

        // A property this very request is setting is not also one waiting to be
        // sent: setting it twice would run the hooks watching it twice over
        if (payload.action === '$set') {
            for (let i = 0; i < (payload.params || []).length; i += 2) delete updates[payload.params[i]];
        }

        return updates;
    }

    /**
     * The properties changed here and not yet answered for by the server.
     *
     * A property is dirty while what the page holds differs from the state the
     * last answer came back with: what the reader has typed and the server has
     * not seen yet. Worked out rather than remembered, so that an answer
     * carrying the very value that was typed leaves nothing dirty behind.
     */
    dirtyFields() {
        const state = this.getState();
        const dirty = new Set();

        // Only what has actually been typed into: a property the server changed
        // on its own was never the reader's to save, and saying it is unsaved
        // would leave the word on the page for as long as the page is open.
        this.formState.touchedFields.forEach((name) => {
            if (JSON.stringify(this.formState.values[name]) !== JSON.stringify(state[name])) dirty.add(name);
        });

        return dirty;
    }

    /** Tell whoever watches which properties are dirty, if that has changed. */
    refreshDirty() {
        const dirty = this.dirtyFields();
        const signature = [...dirty].sort().join(',');

        if (signature === this._dirtySignature) return;

        this._dirtySignature = signature;
        this.formState.dirtyFields = dirty;
        this.dirtyChangeCallbacks.forEach(cb => cb(dirty));
    }

    /**
     * Hand a piece of streamed content to the element it was sent to.
     */
    streamTo(chunk) {
        this.streamUpdateCallbacks.forEach(cb => cb(chunk));
    }

    /**
     * Say in the address bar what is being looked at.
     *
     * Written over rather than pushed: walking ten pages of a list should not
     * put ten entries in the reader's history for the Back button to climb
     * through, and reloading should still come back to the page they were on.
     */
    writeQuery(query) {
        const url = new URL(window.location.href);

        Object.entries(query).forEach(([name, value]) => {
            if (value === null || value === undefined || value === '') url.searchParams.delete(name);
            else url.searchParams.set(name, value);
        });

        if (url.href !== window.location.href) history.replaceState(history.state, '', url.href);
    }

    /**
     * Go back to the top of what has just been drawn again.
     *
     * A reader who was at the bottom of page one is at the bottom of page two
     * otherwise, looking at its last few rows and wondering what happened.
     */
    scrollAfterUpdate(scroll) {
        if (scroll === false) return;

        const target = typeof scroll === 'string'
            ? (this.element.closest(scroll) || document.querySelector(scroll))
            : this.element;

        target?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }

    /**
     * Emit an event from this component, as pb:click="emit('saved')" does.
     */
    emit(event) {
        return window.PyBlade.deliver(event, this.id);
    }

    /**
     * Answer an event this component listens for.
     *
     * What it listens for is read from the snapshot on every event rather than
     * subscribed to once: an event name may be built from what the component
     * holds, and what it holds changes with every answer it gets.
     */
    handleEvent(name, data = {}) {
        const listeners = this.store.get(this.id)?.listeners || {};

        if (!Object.prototype.hasOwnProperty.call(listeners, name)) return;

        return this.sendRequest({ action: '$event', params: [name, data] });
    }

    /**
     * Whether this component is the one named, as emit().to('Dashboard') names it.
     *
     * Either the class on its own or the whole path it is reached by, so that
     * two components of the same name in different modules can be told apart.
     */
    isNamed(name) {
        const path = this.store.get(this.id)?.class || '';

        return path === name || path.split('.').pop() === name;
    }

    // Utility methods for directives
    getState() {
        return this.store.get(this.id)?.state || {};
    }

    navigate(url) {
        return window.PyBlade.navigate(url);
    }

    async refresh() {
        await this.sendRequest({ action: '$refresh' });
    }

    destroy() {
        this.destroyCallbacks.forEach(cb => cb());
        Directives.release(this);
    }
}