QUEUE_SOUND_MODERATION = 'sound moderation'

TICKET_STATUS_NEW = 'new'
TICKET_STATUS_DEFERRED = 'deferred'
TICKET_STATUS_ACCEPTED = 'accepted'
TICKET_STATUS_CLOSED = 'closed'

MODERATION_TEXTS = [
    ('Illegal', "Hey there. Thanks for contributing to Freesound. "
                "Unfortunately we've had to delete this sound. "
                " "
                "Freesound only hosts files that are not copyright infringing. We reject audio taken from copyright "
                "protected media without permission. Please do not upload other people’s works. "
                "Only sounds that you have made yourself or own the copyrights. "
                " "
                "If you'd like to find out what you can upload, please have a look here: "
                 hyperlink_format = '<a href="{https://freesound.org/help/faq/#what-sounds-are-legal-to-put-on-freesound}">{Freesound FAQ - What sounds are legal to put on Freesound?}</a>'
                " "
                "Thanks!"),
    ('Music', "Hey there. Thanks for contributing to Freesound. "
              " "
              "Unfortunately, you've uploaded some music which doesn't fit with the content we allow onto the site. "  
              "We do however allow music samples that are under 1 minute long, not songs. "
              " "
              "Some recommended sites for sharing produced music/songs: "
              "Soundcloud, Bandcamp, CCMixter and The Free Music Archive "
              " "
              "By the way, we welcome material such as loops, riffs, melodies etc. So you could try cutting up your "
              "music into short instrumental loops and uploading them that way. In fact, music and drum loops "
              "are some of the most searched and downloaded sounds on Freesound! "
              " "
              "Thanks for understanding!"),
    ('Not a Sound', "Hey there. Thanks for contributing to Freesound. "
                    "You have uploaded a file that does not fit with the type of content Freesound is looking for. "
                    "Content we reject includes songs, audiobooks, adverts/commercials, podcasts and copyrighted material. "
                    " "
                    "Thanks for understanding!"),
    ('Language', "Hey there. Thanks for contributing to Freesound. "
                 "This is a great sound, but could you possibly add an English title, description and tags? "
                 " "   
                 "You can keep your original description, just add the english in too. This will ensure that your "
                 "sounds are discoverable in the search. Because our user-base is mainly English speaking, it makes "
                 "sense to do this. "
                 " "
                 "Also, please include as much detail as you can in the description. "
                 " "
                 "If you can't find how to edit your sound here's a little visual guide: "
                  hyperlink_format = '<a href="{https://i.imgur.com/s4w2ysv.jpg}">{Guide to editing your upload}</a>'
                 " "
                 "Many thanks!"),
    ('Description/Tags', "Hey there. Thanks for contributing to Freesound "
                         "We noticed that your upload is missing a description / tags. "
                         "Before approving, Please could you update this to include more detail? "
                         "It's important to help other users find your sound in the search. "
                         " "
                         "If you need some guidance on describing please see the following FAQ page: "
                          hyperlink_format = '<a href="{https://freesound.org/help/faq/#how-should-i-describe-my-sounds}">{Freesound FAQ - How should I describe my sounds?}</a>'
                         " "                             
                         "Also, if you can't find how to edit your sound, here's a little visual guide: "
                          hyperlink_format = '<a href="{https://i.imgur.com/s4w2ysv.jpg}">{Guide to editing your upload}</a>'
                         " "
                         "Thanks!"),
    ('Credit Sounds', "Hey there. Thanks for contributing to Freesound. "
                      "We've noticed that you have used one or more sounds from this site that have the "
                      "'Attribution' and/or 'Non-Commercial' license. Other users need to know this, so before we "
                      "can approve it onto the site, we need you to credit these sounds so that everyone can follow "
                      "the respective license terms. "
                      " "
                      "Here is an example of crediting sounds within your description: "
                       hyperlink_format = '<a href="{https://freesound.org/s/544453}">{https://freesound.org/s/544453}</a>'
                      " "
                      "If you can't find how to edit your sound, here's a little visual guide: "
                       hyperlink_format = '<a href="{https://i.imgur.com/s4w2ysv.jpg}">{Guide to editing your upload}</a>'
                      " "
                      "Many thanks!"),
    ('Verify Details', "Hey there. Thanks for contributing to Freesound. "
                       " "
                       "Before we can moderate your upload, could you possibly update the description/tags? "
                       "Any details such as how it was created, recording device, software used, date/location etc-
                       "-are extremely useful.
                       " "
                       "If you can't find how to edit your sound, here's a little visual guide: "
                        hyperlink_format = '<a href="{https://i.imgur.com/s4w2ysv.jpg}">{Guide to editing your upload}</a>'
                       " "
                       "Many thanks! "
                       " "
                       "(If there is no response to this ticket within 2 weeks, the sound will be removed)"),
    ('License Mismatch', "Hey there. Thanks for sharing your work on Freesound. "
                         " "
                         "We noticed that the sound you've edited/remixed and uploaded doesn't match the original CC "
                         "license. This is really important to get correct. "
                         " "
                         "Could you please update the license type of the sound by clicking on 'edit sound information' "
                         "on the sound's download page. "
                         " "
                         "Many thanks!"),
    ('Permission', "Hey there. Thanks for contributing to Freesound. "    
                   "Please could you clarify for us that you have permission to upload the recording of the
                   "performer, singer or speaker to Freesound? "                
                   " "  
                   "It's important that you don't share things that you don't have permission to upload. "
                   " "    
                   "Please let us know "
                   " "
                   "Thanks!"),
     ('Timeout', "Deleting due to the lack of response to the ticket. "
                 "If you believe this was in error, or you didn't have time to respond, "
                 "do feel free to re-upload the sound or get in touch with us. "
                 " "
                 "Thanks for understanding!")
]
