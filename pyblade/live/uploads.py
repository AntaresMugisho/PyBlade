"""A file on its way from the page to wherever it is going to be kept.

Choosing a file does not wait for an action. It is sent on its own, checked
against what the component expects of that property, and put somewhere
temporary; the property is left holding a signed note saying which file it is.
The action that runs later is handed the file and decides where it belongs.

That is what lets a file upload while the rest of a form is still being filled
in, and it is what makes progress and cancelling mean anything: there is a
request of its own to watch, and to stop.

The note the page is given says nothing about where the file is. It is signed,
so a browser can hand it back but cannot write one of its own, and it carries
its own age, so one kept from last week is worth nothing.
"""

import re
from datetime import timedelta
from pathlib import Path
from time import monotonic
from uuid import uuid4

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.utils import timezone

#: Where the files that have not been kept for good yet are put
TEMPORARY_DIRECTORY = "pyblade-tmp"

#: What marks a note out as one of ours, so ordinary text is never mistaken for one
REFERENCE_PREFIX = "pyblade-upload:"

#: What the note is signed with, and how long one is worth anything for
SIGNING_SALT = "pyblade.live.upload"
MAX_AGE = 60 * 60 * 6

#: How often the temporary files are looked over, at most
SWEEP_EVERY = 60 * 60

#: When this process last looked them over, on a clock that only goes forwards
_last_swept = None

_SIZE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(b|kb|mb|gb)?\s*$", re.IGNORECASE)
_SIZE_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}


def parse_size(size):
    """A size written the way people write sizes, in bytes.

    parse_size("2mb")   -> 2097152
    parse_size(4096)    -> 4096
    """
    if isinstance(size, int):
        return size

    match = _SIZE_PATTERN.match(str(size))
    if not match:
        raise ValueError(f"'{size}' is not a size. Write it as a number of bytes, or as '500kb', '2mb' or '1gb'.")

    amount, unit = match.groups()

    return int(float(amount) * _SIZE_UNITS[(unit or "b").lower()])


class MaxFileSize:
    """Refuse a file bigger than the size given.

        rules = {"photo": forms.ImageField(validators=[MaxFileSize("2mb")])}

    Django has a field for everything a file might have to be and no way to say
    how big it may get, so this is the one piece of vocabulary PyBlade adds. It
    is an ordinary validator: it goes wherever Django's own validators go, and
    it is what the upload is refused by before its bytes are kept.
    """

    def __init__(self, size):
        self.size = size
        self.max_bytes = parse_size(size)

    def __call__(self, file):
        if getattr(file, "size", 0) > self.max_bytes:
            raise ValidationError(
                f"This file is too big. It must be no more than {self.size}.",
                code="max_file_size",
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSize) and other.max_bytes == self.max_bytes


class MultipleFileInput(forms.ClearableFileInput):
    """A file input a reader may choose more than one file in."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Ask for several files rather than one.

        rules = {"photos": MultipleFileField(validators=[MaxFileSize("2mb")])}

    Django has no field for several files -- what it offers is the recipe in
    its own documentation -- so PyBlade brings one, and holds every file to
    what the field says rather than only the first.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        one = super().clean

        if not isinstance(data, (list, tuple)):
            data = [] if data in self.empty_values else [data]

        if not data:
            # What an empty list means is what the field says an empty value
            # means, so that `required` is answered in one place
            return one(None, initial) or []

        return [one(file, initial) for file in data]


def is_upload_reference(value):
    """Whether a value is a note saying which file a property holds."""
    return isinstance(value, str) and value.startswith(REFERENCE_PREFIX)


class TemporaryUpload:
    """A file that has been sent but not yet kept for good.

    What an action is handed when a property holds an upload. It knows what the
    file was called, how big it is and what it holds, and it can be opened, kept
    somewhere for good, or thrown away.
    """

    def __init__(self, stored_name, name, size, content_type, reference=None):
        self.stored_name = stored_name
        self.name = name
        self.size = size
        self.content_type = content_type
        self.reference = reference or self._sign()

    def __repr__(self):
        return f"TemporaryUpload(name={self.name!r}, size={self.size})"

    def __str__(self):
        """The note, so that a property holding one travels as one."""
        return self.reference

    def _sign(self):
        payload = {
            "stored_name": self.stored_name,
            "name": self.name,
            "size": self.size,
            "content_type": self.content_type,
        }

        return REFERENCE_PREFIX + signing.dumps(payload, salt=SIGNING_SALT, compress=True)

    @classmethod
    def from_reference(cls, reference, max_age=MAX_AGE):
        """The file a note points at, or None if the note is worth nothing.

        Nothing is raised for a note that was written over or has grown too old:
        a page left open overnight is not a reason to answer with a server error.
        """
        if not is_upload_reference(reference):
            return None

        try:
            payload = signing.loads(reference[len(REFERENCE_PREFIX) :], salt=SIGNING_SALT, max_age=max_age)
        except (signing.BadSignature, signing.SignatureExpired, ValueError):
            return None

        try:
            return cls(
                stored_name=payload["stored_name"],
                name=payload["name"],
                size=payload["size"],
                content_type=payload["content_type"],
                reference=reference,
            )
        except (KeyError, TypeError):
            return None

    def open(self, mode="rb"):
        """The file itself, to read."""
        return default_storage.open(self.stored_name, mode)

    def as_file(self):
        """The file as Django hands one to a form field, for checking."""
        handle = self.open()
        wrapped = File(handle, name=self.name)
        wrapped.content_type = self.content_type

        return wrapped

    def store(self, directory="", name=None):
        """Keep the file for good, and answer where it was put.

            def save(self):
                self.avatar_path = self.photo.store("avatars")

        The temporary one is not left behind: a file that has been kept is not
        one that is still on its way.
        """
        target = str(Path(directory) / (name or self.name)) if directory else (name or self.name)

        with self.open() as handle:
            saved = default_storage.save(target, File(handle, name=target))

        self.delete()

        return saved

    def delete(self):
        """Throw the temporary file away."""
        if default_storage.exists(self.stored_name):
            default_storage.delete(self.stored_name)

    @property
    def url(self):
        """Where the file can be seen while it is still on its way.

        A view of PyBlade's own rather than the media path: a file nobody has
        kept yet is nobody's to stumble on, and what opens it is the same
        signed note the page was given, checked the same way.

        An attribute rather than a method, so that a template may write
        {{ photo.url }}: the template sandbox calls nothing of its own accord
        but the methods of the builtin types.
        """
        from django.urls import reverse

        return reverse("pyblade-preview", args=[self.reference[len(REFERENCE_PREFIX) :]])


def store_temporarily(uploaded_file):
    """Put a file somewhere temporary, and answer with what holds it.

    The name it is kept under is made up here rather than taken from the file:
    what a browser calls a file is the browser's to choose, and two readers
    sending 'photo.jpg' are sending two different photos.
    """
    # Nor does it keep the extension the file came with: a storage served from
    # the site's own address would otherwise serve evil.html as a page. What
    # the file was called travels on the note, and is what it is saved as.
    stored_name = f"{TEMPORARY_DIRECTORY}/{uuid4().hex}"

    saved_name = default_storage.save(stored_name, uploaded_file)

    return TemporaryUpload(
        stored_name=saved_name,
        name=Path(uploaded_file.name or "file").name,
        size=uploaded_file.size,
        content_type=getattr(uploaded_file, "content_type", "") or "application/octet-stream",
    )


def sweep_temporary_uploads(older_than=MAX_AGE):
    """Throw away the files nobody came back for, and answer how many went.

    A file older than the age a note is signed for cannot be claimed by any
    page: whatever note was written for it is worth nothing by now, so the
    bytes are nobody's and are the only thing left to throw away.

    A storage that will not say how old a file is leaves that file where it is.
    What cannot be dated cannot be known to be stale, and deleting it on a
    guess is how a reader loses a photo they are still filling in a form
    around.
    """
    try:
        _, names = default_storage.listdir(TEMPORARY_DIRECTORY)
    except (FileNotFoundError, NotImplementedError, OSError):
        return 0

    cutoff = timezone.now() - timedelta(seconds=older_than)
    swept = 0

    for name in names:
        stored_name = f"{TEMPORARY_DIRECTORY}/{name}"

        try:
            modified = default_storage.get_modified_time(stored_name)
        except (NotImplementedError, FileNotFoundError, OSError):
            continue

        if modified > cutoff:
            continue

        try:
            default_storage.delete(stored_name)
        except OSError:
            # Something else got there first, or the file is not ours to
            # delete; either way it is not worth failing a reader's upload over
            continue

        swept += 1

    return swept


def sweep_if_due(every=SWEEP_EVERY, older_than=MAX_AGE):
    """Sweep, if it has been a while since this process last did.

    Called where files arrive, so that a project taking uploads tidies up after
    itself with nothing to schedule and nothing to install. Answers how many
    went, or None when it was not yet time -- there is no work here that is
    worth doing on every file that arrives.
    """
    global _last_swept

    now = monotonic()

    if _last_swept is not None and now - _last_swept < every:
        return None

    _last_swept = now

    return sweep_temporary_uploads(older_than=older_than)
