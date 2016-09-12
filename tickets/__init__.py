QUEUE_SUPPORT_REQUESTS = 'support requests'
QUEUE_SOUND_MODERATION = 'sound moderation'
QUEUE_BUG_REPORTS      = 'bug reports'
QUEUE_MANAGEMENT       = 'management'

TICKET_STATUS_NEW       = 'new'
TICKET_STATUS_DEFERRED  = 'deferred'
TICKET_STATUS_ACCEPTED  = 'accepted'
TICKET_STATUS_CLOSED    = 'closed'

MODERATION_TEXTS = \
[('Insufficient tags',
  """You have added insufficient tags, please add some more."""),
 ('Insufficient description',
  """The description is not good enough, please add some more details."""),
 ('Incompatible',
  "The sound has an incompatible format and cannot be processed by Freesound. Please convert your file to a different format, such as mp3, wav, or ogg, and upload it again."),
 ('Illegal',
  "The sound you have uploaded is illegal or we suspect you do not own the copyright. Please do not upload it again."),
 ('Not a sound',
  "You have uploaded a file that does not fit with the type of content Freesound is looking for. Songs, for example, should not be on Freesound")]
