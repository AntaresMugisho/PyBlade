/**
 * Reading a form field, and writing one.
 *
 * A property is one thing; the field bound to it is whatever the markup made
 * it. A checkbox on its own says yes or no, several of them sharing a property
 * say which of the choices were ticked, a radio says which one was chosen, and
 * a select taking several gives a list. All of that is here, so that the
 * directive is left with when to send rather than what to send.
 */

/** The kind of field this is, as far as reading and writing it goes. */
function kindOf(el) {
    const tag = (el.tagName || '').toUpperCase();

    if (tag === 'SELECT') return el.multiple ? 'select-multiple' : 'select';
    if (tag !== 'INPUT') return 'text';

    const type = (el.type || 'text').toLowerCase();

    return type === 'checkbox' || type === 'radio' ? type : 'text';
}

/**
 * The other fields bound to the same property.
 *
 * Several checkboxes or radios naming one property are one field between them:
 * what the property holds is read from all of them rather than from the one
 * that happened to be clicked.
 */
function siblings(el, property) {
    if (!property) return [el];

    const root = el.ownerDocument || document;
    const selector = [
        `input[pb\\:model="${property}"]`,
        `input[pb\\:model^="${property}."]`,
    ].join(',');

    let found = [];
    try {
        found = [...root.querySelectorAll(selector)];
    } catch {
        found = [];
    }

    return found.length ? found : [el];
}

/** What a field holds, ready to be sent as the value of the property. */
export function fieldValue(el, property = null) {
    switch (kindOf(el)) {
        case 'checkbox': {
            const group = siblings(el, property);

            // A checkbox on its own is a yes or a no; several of them naming the
            // same property are the choices that were ticked among them
            if (group.length < 2) return !!el.checked;

            return group.filter(box => box.checked).map(box => box.value);
        }

        case 'radio': {
            const chosen = siblings(el, property).find(radio => radio.checked);

            return chosen ? chosen.value : null;
        }

        case 'select-multiple':
            return [...el.options].filter(option => option.selected).map(option => option.value);

        default:
            return el.value;
    }
}

/** Put a value back into a field, as the server saying what it should hold. */
export function writeField(el, value) {
    if (value === undefined) return;

    switch (kindOf(el)) {
        case 'checkbox':
            // A list names the boxes that are ticked; anything else is the
            // yes or no of a checkbox standing on its own
            el.checked = Array.isArray(value) ? value.includes(el.value) : !!value;
            break;

        case 'radio':
            el.checked = el.value === value;
            break;

        case 'select-multiple': {
            const chosen = Array.isArray(value) ? value : [value];

            [...el.options].forEach((option) => { option.selected = chosen.includes(option.value); });
            break;
        }

        default:
            el.value = value === null ? '' : value;
    }
}
