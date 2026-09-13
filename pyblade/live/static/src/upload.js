/**
 * Sending a file, and watching it go.
 *
 * Everything else PyBlade sends goes by fetch, which cannot say how far through
 * sending it is. A file can take a while, and a reader watching nothing happen
 * has no way to tell a slow upload from a broken one -- so this one request is
 * sent the older way, by XMLHttpRequest, which reports the bytes as they go and
 * can be stopped part way.
 *
 * What comes back is a signed note saying which file it is. The property is set
 * to that note like any other value; the file itself stays on the server.
 */

/** What is watching each property being uploaded to, so it can be stopped. */
const inFlight = new Map();

function key(component, property) {
    return `${component.id}:${property}`;
}

/**
 * Send the files chosen for a property, reporting how far along they are.
 *
 * Everything chosen at once goes in the one request, so that a reader watching
 * a bar watches one thing and stopping it stops one thing. Answers what came
 * back -- a note for each file -- or null if it was refused or stopped.
 *
 * A second upload for the same property stops the first: the reader changed
 * their mind, and the one they changed it to is the one that counts.
 */
export function uploadFile(component, property, files, { onProgress } = {}) {
    cancelUpload(component, property);

    const chosen = Array.isArray(files) ? files : [files];
    const total = chosen.reduce((sum, file) => sum + (file.size || 0), 0);

    const body = new FormData();
    chosen.forEach(file => body.append('file', file));
    body.append('property', property);
    body.append('snapshot', JSON.stringify(component.store.get(component.id)));

    const request = new XMLHttpRequest();
    inFlight.set(key(component, property), request);

    return new Promise((resolve) => {
        const done = (value) => {
            inFlight.delete(key(component, property));
            resolve(value);
        };

        request.upload.addEventListener('progress', (event) => {
            if (!event.lengthComputable) return;

            onProgress?.({
                property,
                loaded: event.loaded,
                total: event.total,
                percent: Math.round((event.loaded / event.total) * 100),
            });
        });

        request.addEventListener('load', () => {
            let answer = null;
            try {
                answer = JSON.parse(request.responseText);
            } catch {
                answer = null;
            }

            if (request.status === 200 && answer?.files?.length) {
                onProgress?.({ property, loaded: total, total, percent: 100 });
                done(answer);
                return;
            }

            done({ errors: answer?.errors || [answer?.error || 'The file could not be uploaded.'] });
        });

        // A file that never arrives is not one to keep waiting on
        request.addEventListener('error', () => done({ errors: ['The file could not be uploaded.'] }));
        request.addEventListener('abort', () => done(null));

        request.open('POST', '/pyblade/live/upload/');

        const token = document.querySelector('script[data-csrf]')?.getAttribute('data-csrf');
        if (token) request.setRequestHeader('X-CSRFToken', token);

        request.send(body);
    });
}

/** Stop what is going up for a property, if anything is on its way. */
export function cancelUpload(component, property) {
    const request = inFlight.get(key(component, property));
    if (!request) return false;

    inFlight.delete(key(component, property));
    request.abort();

    return true;
}

/** Whether anything is on its way for a property. */
export function isUploading(component, property) {
    return inFlight.has(key(component, property));
}
