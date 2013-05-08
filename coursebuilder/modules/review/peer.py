# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Internal implementation details of the peer review subsystem.

Public classes, including domain objects, can be found in models/review.py.
Entities declared here should not be used by external clients.
"""

__author__ = [
    'johncox@google.com (John Cox)',
]

from models import entities
from models import models
from models import review
from google.appengine.ext import db

# Identifier for reviews that have been computer-assigned.
ASSIGNER_KIND_AUTO = 'AUTO'
# Identifier for reviews that have been assigned by a human.
ASSIGNER_KIND_HUMAN = 'HUMAN'
ASSIGNER_KINDS = (
    ASSIGNER_KIND_AUTO,
    ASSIGNER_KIND_HUMAN,
)

# State of a review that is currently assigned, either by a human or by machine.
REVIEW_STATE_ASSIGNED = 'ASSIGNED'
# State of a review that is complete and may be shown to the reviewee, provided
# the reviewee is themself in a state to see their reviews.
REVIEW_STATE_COMPLETE = 'COMPLETE'
# State of a review that used to be assigned but the assignment has been
# expired. Only machine-assigned reviews can be expired.
REVIEW_STATE_EXPIRED = 'EXPIRED'
REVIEW_STATES = (
    REVIEW_STATE_ASSIGNED,
    REVIEW_STATE_COMPLETE,
    REVIEW_STATE_EXPIRED,
)


class KeyProperty(db.StringProperty):
    """A property that stores a datastore key.

    App Engine's db.ReferenceProperty is dangerous because accessing a
    ReferenceProperty on a model instance implicitly causes an RPC. We always
    want to know about and be in control of our RPCs, so we use this property
    instead, store a key, and manually make datastore calls when necessary.
    This is analogous to the approach ndb takes, and it also allows us to do
    validation against a key's kind (see __init__).

    Keys are stored as indexed strings internally. Usage:

        class Foo(db.Model):
            pass

        class Bar(db.Model):
            foo_key = KeyProperty(kind=Foo)  # Validates key is of kind 'Foo'.

        foo_key = Foo().put()
        bar = Bar(foo_key=foo_key)
        bar_key = bar.put()
        foo = db.get(bar.foo_key)
    """

    def __init__(self, *args, **kwargs):
        """Constructs a new KeyProperty.

        Args:
            *args: positional arguments passed to superclass.
            **kwargs: keyword arguments passed to superclass. Additionally may
                contain kind, which if passed will be a string used to validate
                key kind. If omitted, any kind is considered valid.
        """
        kind = kwargs.pop('kind', None)
        super(KeyProperty, self).__init__(*args, **kwargs)
        self._kind = kind

    def validate(self, value):
        """Validates passed db.Key value, validating kind passed to ctor."""
        super(KeyProperty, self).validate(str(value))
        if not isinstance(value, db.Key):
            raise db.BadValueError(
                'Value must be of type db.Key; got %s' % type(value))
        if self._kind and value.kind() != self._kind:
            raise db.BadValueError(
                'Key must be of kind %s; was %s' % (self._kind, value.kind()))
        return value


class ReviewSummary(entities.BaseEntity):
    """Object that tracks the aggregate state of reviews for a submission."""

    # UTC last modification timestamp.
    change_date = db.DateTimeProperty(auto_now=True, required=True)
    # UTC create date.
    create_date = db.DateTimeProperty(auto_now_add=True, required=True)

    # Count of ReviewStep entities for this submission currently in state
    # STATE_ASSIGNED.
    assigned_count = db.IntegerProperty(default=0, required=True)
    # Count of ReviewStep entities for this submission currently in state
    # STATE_COMPLETED.
    completed_count = db.IntegerProperty(default=0, required=True)
    # Count of ReviewStep entities for this submission currently in state
    # STATE_EXPIRED.
    expired_count = db.IntegerProperty(default=0, required=True)

    # Key of the submission being reviewed.
    submission_key = KeyProperty(kind=review.Submission, required=True)
    # Identifier of the unit this review is a part of.
    unit_id = db.StringProperty(required=True)


class ReviewStep(entities.BaseEntity):
    """Object that represents a single state of a review."""

    # Audit trail information.

    # Identifier for the kind of thing that did the assignment. Used to
    # distinguish between assignments done by humans and those done by the
    # review subsystem.
    assigner_kind = db.StringProperty(choices=ASSIGNER_KINDS)
    # UTC last modification timestamp.
    change_date = db.DateTimeProperty(auto_now=True, required=True)
    # UTC create date.
    create_date = db.DateTimeProperty(auto_now_add=True, required=True)

    # Repeated data to allow filtering/ordering in queries.

    # Key of the submission being reviewed.
    submission_key = KeyProperty(kind=review.Submission, required=True)
    # Unit this review step is part of.
    unit_id = db.StringProperty(required=True)

    # State information.

    # State of this review step.
    state = db.StringProperty(choices=REVIEW_STATES, required=True)
    # Whether or not the review has been removed. By default removed entities
    # are ignored for most queries.
    removed = db.BooleanProperty(default=False)

    # Pointers that tie the work and people involved together.

    # Key of the Review associated with this step.
    review_key = KeyProperty(kind=review.Review)
    # Key of the associated ReviewSummary.
    review_summary_key = KeyProperty(kind=ReviewSummary)
    # Key of the Student being reviewed.
    reviewee_key = KeyProperty(kind=models.Student)
    # Key of the Student doing this review.
    reviewer_key = KeyProperty(kind=models.Student)
