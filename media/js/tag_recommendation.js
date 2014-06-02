/********************* ONTOLOGY BASED TAG RECOMMENDATION ****************************/

// Needed global variables
var RECOMMENDATION_INTERFACES = [];
var CLIPBOARD = false;
var FOCUSING_OUT = false;
var CURRENT_RECOMMENDATION_KEY = '';
var DRAW_TIMER;
var FOCUSOUT_ADD_TAG_TIMER;
var ADDING_TAG_ON_FOCUSOUT = false;

// INTERFACE OPTIONS
var ALLOW_REMOVE_CATEGORIES = false;
var DRAG_AND_DROP = true;
var CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY = false;  // set to true
var NON_CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY_ON_FIRST_TAG_PER_CATEGORY = !CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY; //false; // set to true
var MAX_NUMBER_OF_RECOMMENDED_TAGS = 20;
var SHOW_CATEGORY_DESCRIPTION_IN_RECOMMENDATIONS_WINDOW = true;
var ADD_TAGS_ON_FOCUSOUT = true;
var ALLOW_INTRODUCING_CATEGORIES_BY_TYPING = true;
var ALLOW_SHOW_HIDE_EXTRA_RECOMMENDED_CATEGORIES = false;
var SHOW_RECOMMENDED_CATEGOIRES_WHEN_NO_INPUT_TAGS = true;
var ALLOW_SHARP_CHARACTER = false;

/*
TAG RECOMMENDATION INTERFACE
 */

function get_recommendation_interface(id){
    return RECOMMENDATION_INTERFACES[id];
}

function create_new_ontology_tag_recommendation_interface_basic_html(id, no_titles){

    if (no_titles == undefined){
        no_titles = false;
    }

    var html = '<div class="tr_tagging_interface_wrapper">'
    if (!no_titles){
        html += '<div class="tr_instructions" style="width:700px;margin-bottom:15px;margin-top:-5px;">Separate tags pressing \'space\' or \'enter\' keys. Join multi-word tags with dashes. For example: field-recording is a popular tag. Use tags with categories to make your sound descriptions more meningful and easily findable to other Freesound users.<br><span style="font-size:80%;">(if you need help, read the <a href="/tagrecommendation/instructions/?b=1" target="_blank">tagging interface instructions</a>)</span></div>'
    }
    html += '<div class="tr_tagging_interface_gray_area">' +
            '<div class="tr_tagline" id="tr_tagline_' + id + '"></div>' +
            '<div class="tr_copypaste" id="tr_copypaste_' + id + '"></div>' +
            '<br style="clear:both">' +
        '</div>' +
        '<div class="tr_recommended_tags tr_hide" id="tr_recommended_tags_' + id + '"></div>' +
        '<div class="tr_category_information" id="tr_category_information_' + id + '"></div>' +
        '<div class="tr_recommended_categories" id="tr_recommended_categories_' + id + '"></div>' +
        '<div class="tr_text_width_measurer" id="tr_text_width_measurer_' + id + '"></div>' +
    '</div>';
    return html;
}

function create_new_ontology_tag_recommendation_interface(id, initial_tags){

    processed_initial_tags = [];
    if (initial_tags != 'None'){
        var inital_tags_parts = initial_tags.split(' ');
        for (i in inital_tags_parts){
            var tag = inital_tags_parts[i];
            if (tag.indexOf(':') != -1){
                var category = tag.split(':')[0];
                var category_tags = tag.split(':').splice(1);
                processed_initial_tags.push({'category':category, 'tags':category_tags});
            } else {
                if (tag) {
                    processed_initial_tags.push({'category':false, 'tags':[tag]});
                }
            }
        }
    }

    var rec_interface = {
        id : id,
        tags: processed_initial_tags, // Tags is a list where every element is a dictionary with category name and tags associated
        writting_category: false,
        adding_tag_for_existing_category: false,
        caret_position_in_input_box: 0,
        current_recommended_tag_categories: [],
        show_more_categories: false,
        current_recommended_tags: false,
        current_recommended_tags_category: false,
        valid_tag_categories: [],
        categories_info: [],
        draw: function(){draw(this)},
        render_tagline_html: function(){return render_tagline_html(this)},
        render_recommended_tags_html: function(){return render_recommended_tags_html(this)},
        render_recommended_categories_html: function(){return render_recommended_categories_html(this)},
        render_category_info_html: function(){return render_category_info_html(this)},
        render_and_draw_copy_paste_icons: function(){ render_and_draw_copy_paste_icons(this)},
        add_event_handlers_to_input_box: function(){add_event_handlers_to_input_box(this)},
        handle_keypress_event: function(e, is_inline){handle_keypress_event(this, e, is_inline)},
        handle_keydown_event: function(e, is_inline){handle_keydown_event(this, e, is_inline)},
        handle_input_box_focusout_event: function(e, is_inline){handle_input_box_focusout_event(this, e, is_inline)},
        handle_input_box_focusin_event: function(e, is_inline){handle_input_box_focusin_event(this, e, is_inline)},
        handle_dropping_tag_into_category_event: function(e, ui){handle_dropping_tag_into_category_event(rec_interface, e, ui)},
        handle_dropping_category_tag_outside_category_event: function(e, ui){handle_dropping_category_tag_outside_category_event(rec_interface, e, ui)},
        get_recommended_tags: function(){get_recommended_tags(this)},
        get_recommended_categories: function(){get_recommended_categories(this)},
        get_already_present_categories: function(){
            var categories = [];
            for (var i in this.tags){
                if (this.tags[i].category){
                    categories.push(this.tags[i].category);
                }
            }
            if (this.writting_category){
                categories.push(this.writting_category);
            }
            return categories;},
        get_already_present_tags: function(){
            var tags = [];
            for (var i in this.tags){
                for (var j in this.tags[i].tags){
                    tags.push(this.tags[i].tags[j]);
                }
            } return tags;},
        get_input_tags: function(separator){
            var input_tags = [];
            for (var i in this.tags){
                if (!this.tags[i].category){
                    for (var j in this.tags[i].tags){
                        input_tags.push(this.tags[i].tags[j]);
                    }
                } else {
                    var current_composed_tag = this.tags[i].category + ':';
                    for (var j in this.tags[i].tags){
                        current_composed_tag += this.tags[i].tags[j]
                        if (j < this.tags[i].tags.length - 1){
                            current_composed_tag += ':';
                        }
                    }
                    input_tags.push(current_composed_tag);
                }
            }
            if (!separator){
                return input_tags.join(',');
            } else {
                return input_tags.join(separator);
            }
        },
        get_category: function(){
            if ((this.writting_category) || (this.adding_tag_for_existing_category)){
                if (this.writting_category){
                    return this.writting_category;
                }
                if (this.adding_tag_for_existing_category){
                    return this.adding_tag_for_existing_category;
                }
            }
        },
        add_tag: function(tag, force_category){
            // Remove non alphanumeric characters and only presevre '-' and '#'
            if (ALLOW_SHARP_CHARACTER){
                tag = tag.replace(/[^a-zA-Z0-9-#]/g,'');
            } else {
                tag = tag.replace(/[^a-zA-Z0-9-]/g,'');
            }

            if (tag.length == 0){
                // if after removal there is no tag, do not add it
                return -1;
            }

            if (!force_category){
                if (!rec_interface.adding_tag_for_existing_category){
                    // Add new tag with or without category
                    if (rec_interface.writting_category){
                        rec_interface.tags.push({'category':rec_interface.writting_category, 'tags':[tag]});
                    } else {
                        rec_interface.tags.push({'category':false, 'tags':[tag]});
                    }
                } else {
                    // Add tag to current existing category
                    for (var i in rec_interface.tags){
                        if (rec_interface.tags[i].category == rec_interface.adding_tag_for_existing_category){
                            rec_interface.tags[i].tags.push(tag);
                        }
                    }
                }
            } else {
                if (rec_interface.get_already_present_categories().indexOf(force_category) == -1){
                    rec_interface.tags.push({'category':force_category, 'tags':[tag]});
                } else {
                    for (var i in rec_interface.tags){
                        if (rec_interface.tags[i].category == force_category){
                            rec_interface.tags[i].tags.push(tag);
                        }
                    }
                }
            }
            rec_interface.get_recommended_categories()
        },
        add_dragged_tag_to_category: function(tag, category, tag_pos_id){
            var pos_i = parseInt(tag_pos_id.split(',')[0], 10);
            var pos_j = parseInt(tag_pos_id.split(',')[1], 10);

            // Add tag to category
            for (var i in rec_interface.tags){
                if (rec_interface.tags[i].category == category){
                    rec_interface.tags[i].tags.push(tag);
                }
            }
            // Remove tag from existing place
            if (!rec_interface.tags[pos_i].category){
                // If moving tag had no category, remove the element from tags array
                rec_interface.tags.splice(pos_i, 1);
            } else {
                // If moving tag had category, remove only the tag from the sub tags array
                rec_interface.tags[pos_i].tags.splice(pos_j, 1);
                // If after dragging the tags for the category are empty, remove the whole element
                if (rec_interface.tags[pos_i].tags.length == 0){
                    rec_interface.tags.splice(pos_i, 1);
                }
            }
            rec_interface.get_recommended_categories();
        },
        add_dragged_tag_to_outside_category: function(tag, category, tag_pos_id){
            // Remove from original category
            var pos_i = parseInt(tag_pos_id.split(',')[0], 10);
            var pos_j = parseInt(tag_pos_id.split(',')[1], 10);
            rec_interface.tags[pos_i].tags.splice(pos_j, 1);
            // If after dragging the tags for the category are empty, remove the whole element
            if (rec_interface.tags[pos_i].tags.length == 0){
                rec_interface.tags.splice(pos_i, 1);
            }
            // Add tag at the end of tags list
            rec_interface.tags.push({'category':false, 'tags':[tag]});
            rec_interface.get_recommended_categories();
        },
        has_at_least_one_tag_per_category: function(category){
            for (var i in this.tags){
                if (this.tags[i].category == category){
                    return true;
                }
            }
            return false;
        }
    };

    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
    rec_interface.render_and_draw_copy_paste_icons();

    // Get all valid tag categories from recommendation server
    $.ajax({
        type: 'POST',
        url: '/tagrecommendation/get_categories/',
        contentType:"application/x-www-form-urlencoded",
        data: {},
        success: function(data) {
            var categories = JSON.parse(data);
            var valid_categories = [];
            var categories_description = {};
            for (var j=0; j < categories.length; j=j+2){
                valid_categories.push(categories[j]);
                categories_description[categories[j]] = categories[j+1];
            }
            rec_interface.valid_tag_categories = valid_categories;
            rec_interface.categories_info = categories_description;
            rec_interface.draw();
            rec_interface.add_event_handlers_to_input_box();
        }
    });
    rec_interface.get_recommended_categories();

    return rec_interface;
}

function draw(rec_interface){
    clearTimeout(DRAW_TIMER);
    /*
    Render html and update div container with new html
     */
    var rendered_tagline = rec_interface.render_tagline_html();
    $('#tr_tagline_' + rec_interface.id).empty().append(rendered_tagline);

    if (DRAG_AND_DROP){
        // Set draggable elements to be draggable
        $('.tr_tag').draggable({
            containment: '.tr_tagline',//'#tr_tagline_' + rec_interface.id,
            cursor: 'move',
            revert: "invalid",
        });

        $('.tr_tag_chained').draggable({
            containment: '.tr_tagline',//'#tr_tagline_' + rec_interface.id,
            cursor: 'move',
            revert: "invalid",
        });

        $('.tr_tag_chained_last').draggable({
            containment: '.tr_tagline',//'#tr_tagline_' + rec_interface.id,
            cursor: 'move',
            revert: "invalid",
        });
        // Set tags with category elements to be droppable
        $('.tr_no_wrapping_tag_with_categories_span').droppable({
            drop: rec_interface.handle_dropping_tag_into_category_event,
            activeClass: "tr_draggable_category",
            greedy:true,
        });

        // Set outer input box draggable
        $('.tr_tagline').droppable({
            drop: rec_interface.handle_dropping_category_tag_outside_category_event,
            activeClass: "tr_draggable_outside_category",
            accept: ".tr_tag_chained,.tr_tag_chained_last",
            greedy:true,
        });
    }

    //var rendered_recommended_tags = rec_interface.render_recommended_tags_html();
    var recommended_tags_element = $('#tr_recommended_tags_' + rec_interface.id);
    // if (!(rec_interface.adding_tag_for_existing_category) && (!rec_interface.writting_category)){
    if (!rec_interface.current_recommended_tags){
        recommended_tags_element.addClass('tr_hide');
    }

    var rendered_recommended_categories = rec_interface.render_recommended_categories_html();
    $('#tr_recommended_categories_' + rec_interface.id).empty().append(rendered_recommended_categories);

    if (!SHOW_CATEGORY_DESCRIPTION_IN_RECOMMENDATIONS_WINDOW){
        var rendered_category_info = rec_interface.render_category_info_html();
        $('#tr_category_information_' + rec_interface.id).empty().append(rendered_category_info);
    }
}

function add_event_handlers_to_input_box(rec_interface){
    var is_inline, input_box_element;
    if (!rec_interface.adding_tag_for_existing_category){
        is_inline = false;
        input_box_element = $('#tr_input_box_' + rec_interface.id);
    } else {
        is_inline = true;
        input_box_element = $('#tr_input_box_inline_' + rec_interface.id);
    }
    input_box_element.keypress(function(e) {
        rec_interface.handle_keypress_event(e, is_inline);
    });

    input_box_element.keydown(function(e) {
        rec_interface.handle_keydown_event(e, is_inline);
    });

    $('#tr_input_box_' + rec_interface.id).focusin(function(e) { // Event for the always showed input box
        if (FOCUSING_OUT){
            clearTimeout(DRAW_TIMER);
            FOCUSING_OUT = false;
            if (!ADDING_TAG_ON_FOCUSOUT){
                rec_interface.draw(); // Enabling this draw breaks the results, we need the timeout
                rec_interface.add_event_handlers_to_input_box();
                $('#tr_input_box_' + rec_interface.id).focus();
            } else {
                setTimeout(function() {
                    rec_interface.draw(); // Enabling this draw breaks the results, we need the timeout
                    rec_interface.add_event_handlers_to_input_box();
                    $('#tr_input_box_' + rec_interface.id).focus();
                }, 120);
            }
        }
    });

    $('#tr_input_box_ext_' + rec_interface.id).focusin(function(e) { // Event for the always showed input box
        if (FOCUSING_OUT){
            clearTimeout(DRAW_TIMER);
            FOCUSING_OUT = false;
            if (!ADDING_TAG_ON_FOCUSOUT){
                rec_interface.draw(); // Enabling this draw breaks the results, we need the timeout
                rec_interface.add_event_handlers_to_input_box();
                $('#tr_input_box_' + rec_interface.id).focus();
            } else {
                setTimeout(function() {
                    rec_interface.draw(); // Enabling this draw breaks the results, we need the timeout
                    rec_interface.add_event_handlers_to_input_box();
                    $('#tr_input_box_' + rec_interface.id).focus();
                }, 120);
            }
        }
    });

    input_box_element.blur(function(e) {
        rec_interface.handle_input_box_focusout_event(e, is_inline);
    });

    //input_box_element.focusin(function(e) {
        //rec_interface.handle_input_box_focusin_event(e, is_inline);
    //});
}

function render_tagline_html(rec_interface){
    /*
    Render html version of the tags
     */
    html = '';
    for (var i in rec_interface.tags){
        var tag_struct = rec_interface.tags[i];
        if (tag_struct.category != false){
            html += '<span id="' + tag_struct.category + '" class="tr_no_wrapping_tag_with_categories_span">';
            // Display category
            var category_css_class = 'tr_tag_category';
            if ((rec_interface.writting_category == tag_struct.category) || (rec_interface.adding_tag_for_existing_category == tag_struct.category)){
                category_css_class = 'tr_tag_category_selected';
            }
            html += '<span class="' + category_css_class + '">' + tag_struct.category;
            // Add temove link
            if (ALLOW_REMOVE_CATEGORIES){
                html += '<a class="tr_remove_tag_icon" href="javascript:void(0)" style="margin-left:2px;" onclick=delete_tag_struct_from_tag_struct_id(' + rec_interface.id + ',' + i + ')></a>'
            }
            html += '<a class="tr_add_tag_icon" href="javascript:void(0)" style="margin-left:2px;" onclick=add_new_tag_for_category(' + rec_interface.id + ',"' + tag_struct.category + '")></a>'
            html += '</span>';
        }
        // Display tags (if there is no category there should be no more than one tag...
        for (var j in tag_struct.tags){
            var tag = tag_struct.tags[j];
            var tag_css_class = 'tr_tag';
            if (j < tag_struct.tags.length -1){
                // Use chained class
                tag_css_class = 'tr_tag_chained';
            } else if ((j == tag_struct.tags.length -1) && (tag_struct.category)) {
                tag_css_class = 'tr_tag_chained_last';
            }
            html += '<span id="' + i + ',' + j + '" class="' + tag_css_class + '">' + tag;
            // Add remove link
            html += '<a class="tr_remove_tag_icon" href="javascript:void(0)" style="margin-left:2px;" onclick=delete_tag_from_tag_id(' + rec_interface.id + ',' + i + ',' + j + ')></a>'
            html += '</span>';
        }
        if (tag_struct.category != false){
            html += '</span>';
        }
        // Dislpay inline input box if adding tags to an existing category
        if ((rec_interface.adding_tag_for_existing_category) && (rec_interface.adding_tag_for_existing_category == tag_struct.category)){
            html += '<span id="tr_ib_pos_' + rec_interface.id + '" class="tr_input_box_inline_wrapper"><input type="text" class="tr_input_box_inline" autocomplete="off" id="tr_input_box_inline_' + rec_interface.id + '"></span>';
            if ((rec_interface.adding_tag_for_existing_category) && (CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY)){
                html += '&nbsp;&nbsp;&nbsp;'
            }
        }

        html += ' ';
    }

    // Display inputbox for new tags and set focus
    if ((!rec_interface.adding_tag_for_existing_category) || (CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY)){
        html += ' <span class="tr_no_wrapping_span">';
        if (rec_interface.writting_category){
            html += '<span class="tr_tag_category_selected">' + rec_interface.writting_category;
            if (ALLOW_REMOVE_CATEGORIES){
                html += '<a class="tr_remove_tag_icon" href="javascript:void(0)" style="margin-left:2px;" onclick=delete_tag_writting_category(' + rec_interface.id + ')></a>'
            }
            html += '</span>';
            // display input box
            if (CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY){
                html += '<span id="tr_ib_pos_' + rec_interface.id + '" class="tr_input_box_wrapper"><input type="text" placeholder="" class="tr_input_box_inline" autocomplete="off" id="tr_input_box_' + rec_interface.id + '"></span>';
                html += '</span>&nbsp;&nbsp;&nbsp;';
            }
        }
        var input_box_css_class = 'tr_input_box';
        var input_box_placeholder = '...';
        if ((rec_interface.tags.length == 0) && (rec_interface.writting_category == false)){
            input_box_css_class = 'tr_input_box'; //'tr_first_input_box';
            input_box_placeholder = '...'; //'type here...';
        }
        var input_box_base_id = 'tr_input_box_';
        if ((!rec_interface.adding_tag_for_existing_category) || (CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY)){
            if (rec_interface.writting_category){
                if (CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY){
                    input_box_base_id = 'tr_input_box_ext_';
                }
            }
        }

        html += '<span id="tr_ib_pos_' + rec_interface.id + '" class="tr_input_box_wrapper"><input type="text" placeholder="' + input_box_placeholder + '" class="' + input_box_css_class + '" autocomplete="off" id="' + input_box_base_id + rec_interface.id + '"></span>';
        html += '</span>';
    }

    if (rec_interface.tags.length == 0){
        html += '<span style="color:#bbbbbb;font-size:13px;">&nbsp;&nbsp;&nbsp;< start introducing tags by typing here...</span>';
    }

    return html
}

function render_recommended_tags_html(rec_interface){
    if (rec_interface.current_recommended_tags){
        var already_present = rec_interface.get_already_present_tags();
        html = '';
        html += '<div class="tag_recommendation_close_button"><a href="javascript:void(0)" onclick="this.addClass(\'tr_hide\');">x</a></div>';
        if (SHOW_CATEGORY_DESCRIPTION_IN_RECOMMENDATIONS_WINDOW){
            var category = rec_interface.current_recommended_tags_category;
            var description = rec_interface.categories_info[category];
            if (description){
                description = description.replace(category, '<span class="tr_category_name_in_description">' + category + '</span>');
            }
            html += '<div class="tr_recommended_tags_info"><div class="tr_tag_category_description">' + description + '</div>';
            html += 'Tag suggestions: <span style="color:grey;font-size:10px;">(click on these tags or type your own)</span>';
            html += '</div>';
        } else {
            html += '<div class="tr_recommended_tags_info">Tag suggestions: <span style="color:grey;font-size:10px;">(click on these tags or type your own)</span></div>';
        }
        html += '<br style="clear:both">';
        var added = 0;
        for (var i in rec_interface.current_recommended_tags){
            var tag = rec_interface.current_recommended_tags[i];
            if (already_present.indexOf(tag) == -1){
                html += '<a href="javascript:void(0)" onclick=add_tag_from_recommendation(' + rec_interface.id + ',"' + tag + '","' + rec_interface.current_recommended_tags_category + '")>' +
                    '<span class="tr_tag_in_recommendation_list">' + tag + '</span></a> ';
                added += 1;
                if (added == MAX_NUMBER_OF_RECOMMENDED_TAGS){
                    break;
                }
            }
        }
        if (added == 0){
            if (SHOW_CATEGORY_DESCRIPTION_IN_RECOMMENDATIONS_WINDOW){
                html += 'no recommended tags...'
            } else {
                return '';
            }
        }
        return html;
    } else {
        return '';
    }
}

function render_recommended_categories_html(rec_interface){
    var recommended_categories = rec_interface.current_recommended_tag_categories;
    var already_present = rec_interface.get_already_present_categories();
    var filtered_recommended_categories = [];
    for (var i in recommended_categories){
        var category = recommended_categories[i];
        if (already_present.indexOf(category) == -1){
            filtered_recommended_categories.push(category);
        }
    }
    var extra_categories = [];

    for (var i in rec_interface.valid_tag_categories){
        var category = rec_interface.valid_tag_categories[i];
        if ((filtered_recommended_categories.indexOf(category) == -1) && (already_present.indexOf(category) == -1)){
            extra_categories.push(category);
        }
    }

    html = '';
    if (filtered_recommended_categories.length > 0){
        if (rec_interface.tags.length > 0){
            html += 'Recommended tag categories:<br>'
        } else {
            html += 'Tag categories:<br>'
        }
        for (var i in filtered_recommended_categories){
            var category = filtered_recommended_categories[i];
            html += '<a href="javascript:void(0)" onclick=add_category_from_recommendation(' + rec_interface.id + ',"' + category + '")>' +
                '<span class="tr_tag_category">' + category + '</span></a> ';
        }
    }

    if (extra_categories.length > 0){
        if (!rec_interface.show_more_categories){
            if (rec_interface.tags.length > 0){
                if (ALLOW_SHOW_HIDE_EXTRA_RECOMMENDED_CATEGORIES){
                    html += '<div id="extra_recommended_categories_button_' + rec_interface.id + '"><a href="javascript:void(0)" onclick="show_extra_recommendation(' + rec_interface.id + ')">more categories...</a></div>'
                } else {
                    html += '<br>Other tag categories:<br>'
                }
            }
            var extra_categories_html = '';
            if (rec_interface.tags.length > 0){
                if (ALLOW_SHOW_HIDE_EXTRA_RECOMMENDED_CATEGORIES){
                    extra_categories_html += '<div id="extra_recommended_categories_' + rec_interface.id + '" style="display:none;"><a href="javascript:void(0)" onclick="hide_extra_recommendation(' + rec_interface.id + ')">less categories...</a><br>'
                }
            }
            for (var i in extra_categories){
                var category = extra_categories[i];
                extra_categories_html += '<a href="javascript:void(0)" onclick=add_category_from_recommendation(' + rec_interface.id + ',"' + category + '")>' +
                    '<span class="tr_tag_category">' + category + '</span></a> ';
            }
            if (rec_interface.tags.length > 0){
                extra_categories_html += '</div>'
            }
            html += extra_categories_html;
        } else {
            if (rec_interface.tags.length > 0){
                if (ALLOW_SHOW_HIDE_EXTRA_RECOMMENDED_CATEGORIES){
                    html += '<div id="extra_recommended_categories_button_' + rec_interface.id + '" style="display:none;"><a href="javascript:void(0)" onclick="show_extra_recommendation(' + rec_interface.id + ')">more categories...</a></div>'
                }
            }
            var extra_categories_html = '';
            if (rec_interface.tags.length > 0){
                if (ALLOW_SHOW_HIDE_EXTRA_RECOMMENDED_CATEGORIES){
                    extra_categories_html += '<div id="extra_recommended_categories_' + rec_interface.id + '"><a href="javascript:void(0)" onclick="hide_extra_recommendation(' + rec_interface.id + ')">less categories...</a><br>'
                }
            }
            for (var i in extra_categories){
                var category = extra_categories[i];
                extra_categories_html += '<a href="javascript:void(0)" onclick=add_category_from_recommendation(' + rec_interface.id + ',"' + category + '")>' +
                    '<span class="tr_tag_category">' + category + '</span></a> ';
            }
            if (rec_interface.tags.length > 0){
                extra_categories_html += '</div>'
            }
            html += extra_categories_html;
        }
    }

    return html;
}

function render_category_info_html(rec_interface){
    html = '';
    if ((rec_interface.writting_category) || (rec_interface.adding_tag_for_existing_category)){
        var description;
        if (rec_interface.writting_category){
            description = rec_interface.categories_info[rec_interface.writting_category];
            if (description){
                description = description.replace(rec_interface.writting_category, '<span class="tr_category_name_in_description">' + rec_interface.writting_category + '</span>');
            }
        }
        if (rec_interface.adding_tag_for_existing_category){
            description = rec_interface.categories_info[rec_interface.adding_tag_for_existing_category];
            if (description){
                description = description.replace(rec_interface.adding_tag_for_existing_category, '<span class="tr_category_name_in_description">' + rec_interface.adding_tag_for_existing_category + '</span>');
            }
        }
        if (description){
            html += description;
        }
    }
    return html;
}

function render_and_draw_copy_paste_icons(rec_interface){

    var html = '';
    if (INTERFACE_IDS.length > 1){
        html += '<a class="tr_button_icon" href="javascript:void(0)" onclick=copy_current_tagline(' + rec_interface.id + ')><img src="' + MEDIA_URL + 'images/tagrecommendation/document-copy.png" alt="copy" title="copy"/></a>'
        html +='<a class="tr_button_icon" href="javascript:void(0)" onclick=paste_current_tagline(' + rec_interface.id + ')><img src="' + MEDIA_URL + 'images/tagrecommendation/clipboard-paste.png" alt="paste" title="paste"/></a>'
    }
    html +='<a class="tr_button_icon" href="javascript:void(0)" onclick=reset_current_tagline(' + rec_interface.id + ')><img src="' + MEDIA_URL + 'images/tagrecommendation/mail_delete.png" alt="delete" title="delete"/></a>'
    $('#tr_copypaste_' + rec_interface.id).empty().append(html);
}

function handle_keypress_event(rec_interface, e, is_inline){
    /*
    Handle keypress event on input box
    If key pressed is 13 (enter) or 32 (space), we add the contents of input box as new tag
    */
    var base_id = '#tr_input_box_';
    if (is_inline){
        base_id = '#tr_input_box_inline_';
    }
    var input_box_element = $(base_id + rec_interface.id);

    if ((e.which == 13) || (e.which == 32)){
        if (input_box_element.val().match(/[^ ]+/g)){
            rec_interface.add_tag(input_box_element.val());
            rec_interface.get_recommended_categories();

            if ((rec_interface.writting_category) && (CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY) && (!NON_CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY_ON_FIRST_TAG_PER_CATEGORY)){
                rec_interface.adding_tag_for_existing_category = rec_interface.writting_category;
            }
            rec_interface.writting_category = false;
            if (!CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY){
                rec_interface.adding_tag_for_existing_category = false;
            }
            rec_interface.current_recommended_tags = false;
            rec_interface.current_recommended_tags_category = false;
            rec_interface.draw();
            rec_interface.add_event_handlers_to_input_box();

            if (rec_interface.adding_tag_for_existing_category){
                $('#tr_input_box_inline_' + rec_interface.id).focus();
                rec_interface.get_recommended_categories();
                rec_interface.get_recommended_tags();
            } else {
                $(base_id + rec_interface.id).focus();
            }
        }
        e.preventDefault();
    }
    if (e.which == 58){
        if (ALLOW_INTRODUCING_CATEGORIES_BY_TYPING){
            var category = input_box_element.val();
            var valid_categories = rec_interface.valid_tag_categories;
            if ((!rec_interface.writting_category) && (!rec_interface.adding_tag_for_existing_category)){
                if (valid_categories.indexOf(category) != -1){
                    if (rec_interface.get_already_present_categories().indexOf(category) == -1){
                        rec_interface.writting_category = category;
                        rec_interface.draw();
                        rec_interface.add_event_handlers_to_input_box();
                        $('#tr_input_box_' + rec_interface.id).focus();
                        rec_interface.get_recommended_categories();
                        rec_interface.get_recommended_tags();
                    } else {
                        // If category already eists, switch to adding tag for existing category
                        rec_interface.adding_tag_for_existing_category = category;
                        rec_interface.draw();
                        rec_interface.add_event_handlers_to_input_box();
                        $('#tr_input_box_inline_' + rec_interface.id).focus();
                        rec_interface.get_recommended_categories();
                        rec_interface.get_recommended_tags();
                    }
                }
            }
        }
        // Prevent use of ':', it may break things later
        e.preventDefault();
    }
}

function handle_keydown_event(rec_interface, e, is_inline){
    var base_id = '#tr_input_box_';
    if (is_inline){
        base_id = '#tr_input_box_inline_';
    }
    var new_input_box_element = $(base_id + rec_interface.id);
    var rendered_fake_div = $("#tr_text_width_measurer_" + rec_interface.id);
    rendered_fake_div.empty().html(new_input_box_element.val());
    var width = (rendered_fake_div.width() + 10) + "px";
    new_input_box_element.css('width', width);
}

function handle_input_box_focusout_event(rec_interface, e, is_inline){
    FOCUSING_OUT = true;
    var base_id = '#tr_input_box_';
    if (is_inline){
        base_id = '#tr_input_box_inline_';
    }
    var input_box_element = $(base_id + rec_interface.id);
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    if (is_inline){
        if (ADD_TAGS_ON_FOCUSOUT){
            var current_category = rec_interface.get_category();
            var current_input = input_box_element.val();
            ADDING_TAG_ON_FOCUSOUT = true;
            FOCUSOUT_ADD_TAG_TIMER = setTimeout(function() {
                rec_interface.add_tag(current_input, current_category);
            }, 100);
        }
        rec_interface.writting_category = false;
        rec_interface.adding_tag_for_existing_category = false;
        if (!ADD_TAGS_ON_FOCUSOUT){
            input_box_element.val('');
        }
        handle_keydown_event(rec_interface, false, true); // resize the input box
        DRAW_TIMER = setTimeout(function() {
            rec_interface.draw(); // Enabling this draw breaks the results, we need the timeout
            rec_interface.add_event_handlers_to_input_box();
        }, 300);
    } else {
        if (ADD_TAGS_ON_FOCUSOUT){
            var current_category = rec_interface.get_category();
            var current_input = input_box_element.val();
            ADDING_TAG_ON_FOCUSOUT = true;
            FOCUSOUT_ADD_TAG_TIMER = setTimeout(function() {
                rec_interface.add_tag(current_input, current_category);
            }, 100);
        }
        rec_interface.writting_category = false;
        rec_interface.adding_tag_for_existing_category = false;
        if (!ADD_TAGS_ON_FOCUSOUT){
            input_box_element.val('');
        }
        handle_keydown_event(rec_interface, false, false); // resize the input box
        //rec_interface.draw(); // Enabling this draw breaks the results
        //rec_interface.add_event_handlers_to_input_box();
        DRAW_TIMER = setTimeout(function() {
            rec_interface.draw(); // Enabling this draw breaks the results, we need the timeout
            rec_interface.add_event_handlers_to_input_box();
        }, 300);
    }
}

function handle_input_box_focusin_event(rec_interface, e, is_inline){
    var base_id = '#tr_input_box_';
    if (is_inline){
        base_id = '#tr_input_box_inline_';
    }
    var input_box_element = $(base_id + rec_interface.id);
    rec_interface.add_event_handlers_to_input_box();
}

function handle_dropping_tag_into_category_event(rec_interface, e, ui){
    log('DragAndDropTagIntoCategory');
    var tag = ui.draggable[0].innerText;
    var tag_pos_id = ui.draggable[0].id;
    var category = e.target.id;
    rec_interface.add_dragged_tag_to_category(tag, category, tag_pos_id);
    rec_interface.writting_category = false;
    rec_interface.adding_tag_for_existing_category = false;
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
}

function handle_dropping_category_tag_outside_category_event(rec_interface, e, ui){
    log('DragAndDropTagOutsideCategory');
    var tag = ui.draggable[0].innerText;
    var tag_pos_id = ui.draggable[0].id;
    var category = e.target.id;
    rec_interface.add_dragged_tag_to_outside_category(tag, category, tag_pos_id);
    rec_interface.writting_category = false;
    rec_interface.adding_tag_for_existing_category = false;
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
}


function delete_tag_from_tag_id(rec_interface_id, tag_struct_id, tag_id){
    var rec_interface = get_recommendation_interface(rec_interface_id);
    var tag_struct = rec_interface.tags[tag_struct_id];
    if (tag_struct.tags.length == 1){
        rec_interface.tags.splice(tag_struct_id, 1);
    } else {
        tag_struct.tags.splice(tag_id, 1);
    }
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
    rec_interface.get_recommended_categories();
}

function delete_tag_struct_from_tag_struct_id(rec_interface_id, tag_struct_id){
    var rec_interface = get_recommendation_interface(rec_interface_id);
    rec_interface.tags.splice(tag_struct_id, 1);
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
    rec_interface.get_recommended_categories();
}

function delete_tag_writting_category(rec_interface_id){
    var rec_interface = get_recommendation_interface(rec_interface_id);
    rec_interface.writting_category = false;
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
}

function add_category_from_recommendation(rec_interface_id, category){
    log('AddedCategory::' + category);
    var rec_interface = get_recommendation_interface(rec_interface_id);
    rec_interface.writting_category = category;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
    $('#tr_input_box_' + rec_interface.id).focus();
    rec_interface.get_recommended_tags();
}

function add_new_tag_for_category(rec_interface_id, category){
    var rec_interface = get_recommendation_interface(rec_interface_id)
    rec_interface.writting_category = false;
    rec_interface.adding_tag_for_existing_category = category;
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
    $('#tr_input_box_inline_' + rec_interface.id).focus();
    rec_interface.get_recommended_categories();
    rec_interface.get_recommended_tags();
}

function add_tag_from_recommendation(rec_interface_id, tag, category){
    log('AddedTag::' + tag + '|forCategory::' + category);
    clearTimeout(FOCUSOUT_ADD_TAG_TIMER);
    var rec_interface = get_recommendation_interface(rec_interface_id);
    if (category){
        rec_interface.writting_category = category;
    }
    if (rec_interface.has_at_least_one_tag_per_category(category)){
        rec_interface.adding_tag_for_existing_category = category;
    }
    rec_interface.add_tag(tag);
    rec_interface.writting_category = false;
    if ((!CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY) && (rec_interface.adding_tag_for_existing_category)){
        rec_interface.adding_tag_for_existing_category = false;
    }
    if (!NON_CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY_ON_FIRST_TAG_PER_CATEGORY){
        rec_interface.adding_tag_for_existing_category = category;
    }
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.draw();
    if ((CONTINUOUS_ADD_TAGS_FROM_EXISTING_CATEGORY) && (rec_interface.adding_tag_for_existing_category)){
        $('#tr_input_box_inline_' + rec_interface.id).focus();
        rec_interface.get_recommended_categories();
        rec_interface.get_recommended_tags();
    }
    rec_interface.add_event_handlers_to_input_box();
}

function show_extra_recommendation(rec_interface_id){
    get_recommendation_interface(rec_interface_id).show_more_categories = true;
    $('#extra_recommended_categories_' + rec_interface_id).show();
    $('#extra_recommended_categories_button_' + rec_interface_id).hide();
}

function hide_extra_recommendation(rec_interface_id){
    get_recommendation_interface(rec_interface_id).show_more_categories = false;
    $('#extra_recommended_categories_' + rec_interface_id).hide();
    $('#extra_recommended_categories_button_' + rec_interface_id).show();
}

function copy_current_tagline(rec_interface_id){
    var rec_interface = get_recommendation_interface(rec_interface_id);
    CLIPBOARD = rec_interface.tags;
}

function paste_current_tagline(rec_interface_id){
    if (CLIPBOARD){
        var rec_interface = get_recommendation_interface(rec_interface_id);
        rec_interface.tags = CLIPBOARD;
        rec_interface.writting_category = false;
        rec_interface.adding_tag_for_existing_category = false;
        rec_interface.current_recommended_tags = false;
        rec_interface.current_recommended_tags_category = false;
        rec_interface.current_recommended_categories = [];
        rec_interface.draw();
        rec_interface.add_event_handlers_to_input_box();
        rec_interface.get_recommended_categories();

        CLIPBOARD = false;
    }
}

function reset_current_tagline(rec_interface_id){
    var rec_interface = get_recommendation_interface(rec_interface_id);
    rec_interface.tags = [];
    rec_interface.writting_category = false;
    rec_interface.adding_tag_for_existing_category = false;
    rec_interface.current_recommended_tags = false;
    rec_interface.current_recommended_tags_category = false;
    rec_interface.current_recommended_categories = [];
    rec_interface.draw();
    rec_interface.add_event_handlers_to_input_box();
    rec_interface.get_recommended_categories();
}

function get_recommended_categories(rec_interface){
    /*
    Get a set of recommended categories given a tagline
    */

    $.ajax({
        type: 'POST',
        url: '/tagrecommendation/get_recommended_categories/',
        contentType:"application/x-www-form-urlencoded",
        data: {
            input_tags: rec_interface.get_input_tags()
        },
        success: function(data) {
            var categories = JSON.parse(data);
            if (categories.length > 0){
                rec_interface.current_recommended_tag_categories = categories;
                var rendered_recommended_categories = rec_interface.render_recommended_categories_html();
                $('#tr_recommended_categories_' + rec_interface.id).empty().append(rendered_recommended_categories);
            }
        }
    });
}

function get_recommended_tags(rec_interface){
    /*
    Get a set of recommended tags per a tag category or return false if the requested category does not exist
    */
    var input_tags = rec_interface.get_input_tags();
    var category_name = rec_interface.get_category();
    var recommendation_key = input_tags + '|' + category_name;
    if (recommendation_key != CURRENT_RECOMMENDATION_KEY){
        $.ajax({
            type: 'POST',
            url: '/tagrecommendation/get_recommendation/',
            contentType:"application/x-www-form-urlencoded",
            data: {
                input_tags: input_tags,
                category: category_name
            },
            success: function(data) {
                var parsed_data = JSON.parse(data);
                var recommendations = parsed_data.tags;
                var audio_category = parsed_data.audio_category;
                CURRENT_RECOMMENDATION = recommendations;
                CURRENT_RECOMMENDATION_KEY = recommendation_key;
                rec_interface.current_recommended_tags = recommendations;
                rec_interface.current_recommended_tags_category = category_name;
                log('RecommendationForInputTags::' + rec_interface.get_input_tags() + '|withRecommendedTags::' + recommendations.join(',') + '|forCategory::' + category_name);

                var rendered_recommended_tags = rec_interface.render_recommended_tags_html();
                if (rendered_recommended_tags.length > 0){
                    var recommended_tags_element = $('#tr_recommended_tags_' + rec_interface.id);
                    recommended_tags_element.empty().append(rendered_recommended_tags);
                    var input_box_ref_element = $('#tr_ib_pos_' + rec_interface.id);
                    var x=input_box_ref_element.offset().left;
                    var y=input_box_ref_element.offset().top;
                    recommended_tags_element.css({left:x,top:y+28});
                    recommended_tags_element.removeClass('tr_hide');
                } else {
                    var recommended_tags_element = $('#tr_recommended_tags_' + rec_interface.id);
                    recommended_tags_element.addClass('tr_hide');
                }
            }
        });
    } else {
        rec_interface.current_recommended_tags = CURRENT_RECOMMENDATION;
        rec_interface.current_recommended_tags_category = category_name;


        var rendered_recommended_tags = rec_interface.render_recommended_tags_html();
        if (rendered_recommended_tags.length > 0){
            var recommended_tags_element = $('#tr_recommended_tags_' + rec_interface.id);
            recommended_tags_element.empty().append(rendered_recommended_tags);
            var input_box_ref_element = $('#tr_ib_pos_' + rec_interface.id);
            var x=input_box_ref_element.offset().left;
            var y=input_box_ref_element.offset().top;
            recommended_tags_element.css({left:x,top:y+28});
            recommended_tags_element.removeClass('tr_hide');
        } else {
            var recommended_tags_element = $('#tr_recommended_tags_' + rec_interface.id);
            recommended_tags_element.addClass('tr_hide');
        }
        /*
        var rendered_recommended_tags = rec_interface.render_recommended_tags_html();
        var recommended_tags_element = $('#tr_recommended_tags_' + rec_interface.id);
        recommended_tags_element.empty().append(rendered_recommended_tags);
        var input_box_ref_element = $('#tr_ib_pos_' + rec_interface.id);
        var x=input_box_ref_element.offset().left;
        var y=input_box_ref_element.offset().top;
        recommended_tags_element.css({left:x,top:y+28});
        recommended_tags_element.removeClass('tr_hide');
        */
    }
}

/********************* CURRENT TAG RECOMMENDATION ****************************/

// Needed global variables
//var RECOMMENDATION_INTERFACES = [];
//var CURRENT_RECOMMENDATION_KEY = '';
var CURRENT_RECOMMENDATION = '';
var CURRENT_AUDIO_CATEGORY = '';
var TIMER;
var DONE_TYPING_INTERVAL = 500;


function create_new_current_tag_recommendation_interface_basic_html(id, no_titles){

    var html = '<div class="tr_tagging_interface_wrapper">'
    if (!no_titles){
        html += '<div class="tr_instructions" style="margin-bottom:15px;margin-top:-5px;">Separate tags with spaces. Join multi-word tags with dashes. For example: field-recording is a popular tag.<br><span style="font-size:80%;">(if you need help, read the <a href="/tagrecommendation/instructions/?a=1" target="_blank">tagging interface instructions</a>)</span></div>'
    }
    html += '<div class="tr_tagging_interface_gray_area">' +
            '<textarea class="input_text" id="cur_interface_it_' + id + '" style="font-size:13px;height:40px;width:775px;"></textarea>' +
        '</div>' +
        '<div class="tr_recommended_tags_list_area" style="width:700px;margin-top:10px;margin-left:5px;" id="recommended_tags_div_' + id + '"></div>' +
    '</div>';

    return html;
}

function create_new_current_tag_recommendation_interface(id){

    var rec_interface = {
        id : id,
        get_recommended_tags: function(){current_get_recommended_tags(this)},
        clear_recommendations: function(){current_draw_recommended_tags(this, [], null)},
        draw_recommended_tags: function(recommendations, audio_category){current_draw_recommended_tags(this, recommendations, audio_category)},
        get_input_tags: function(){
            var raw_input_tags = $('#cur_interface_it_' + rec_interface.id).val().replace(/\n/g, " ");;
            var parsed_input_tags = raw_input_tags.match(/[^ ]+/g)
            var input_tags = false;
            if (parsed_input_tags){
                return parsed_input_tags.join(',');
            } else {
                return '';
            }
        }
    };

    // Listen to keyup events
    var textarea_element = $('#cur_interface_it_' + id);
    textarea_element.keyup(function(event) {
        clearTimeout(TIMER);
        var textarea_id = $(this)[0].id;
        var textarea_element = $("#cur_interface_it_" + textarea_id);
        if (textarea_element.val() != "") {
            // recommend tags when last introduced character is " " or "\n"
            if  ((event.keyCode == 32) || (event.keyCode == 13)) { // " " or "\n"
                get_recommendation_interface(id).get_recommended_tags();
            }
            TIMER = setTimeout(function(){
                get_recommendation_interface(id).get_recommended_tags();
            }, DONE_TYPING_INTERVAL);
        } else {
            get_recommendation_interface(id).clear_recommendations();
        }
    });

    // Listen to cut, paste and focusin events to recommend tags
    textarea_element.bind('cut paste', function() {
        var textarea_id = $(this)[0].id;
        get_recommendation_interface(id).get_recommended_tags();
    });

    return rec_interface;
}

function current_draw_recommended_tags(rec_interface, recommendations, audio_category){

    if (recommendations.length > 0){

        var recommendation_element = $("#recommended_tags_div_" + rec_interface.id);
        recommendation_element.empty();
        recommendation_element.append("<span style=\"color: #bccb79;font-size:12px;\">Suggestions of other possibly relevant tags given your input&nbsp</span> (click on the tags to add them to your list)");

        var html = "";
        html += "<ul id=\"recommended_tags_div_list_" + rec_interface.id + "\">";
        for (var i in recommendations){
            html += "<li class=\"tr_tag\" id=\"" + recommendations[i] + "_" + rec_interface.id + "\"><a href=\"javascript:void(0);\" onclick=\"current_add_tag(\'" + rec_interface.id + "\',\'" + recommendations[i] + "\')\">" + recommendations[i] + "</a></li>"
        }
        html += "</ul><br>";
        recommendation_element.append(html);

        var rec_list_element = $("#recommended_tags_div_list_" + rec_interface.id);
        rec_list_element.css("margin-left","-40px");

    }else{
        var recommendation_element = $("#recommended_tags_div_" + rec_interface.id);
        recommendation_element.empty();
    }
}

function current_add_tag(rec_interface_id, tag){

    log('AddedTag::' + tag);

    var ask_for_more = false;
    var textarea_element = $("#cur_interface_it_" + rec_interface_id);
    var separator = " ";
    if (!$.trim(textarea_element.val())) {
        ask_for_more = true;
        separator = "";
    }

    textarea_element.val(textarea_element.val() + separator + tag);
    $("#" + tag + "_" + rec_interface_id).remove();

    var remaining_tags = $("#recommended_tags_div_list_" + rec_interface_id).children().length;
    if (remaining_tags > 1){
    }else{
        ask_for_more = true
    }

    if (ask_for_more == true){
        get_recommendation_interface(rec_interface_id).get_recommended_tags();
    }
}

function current_get_recommended_tags(rec_interface){
    /*
    Get a set of recommended tags per a tag category or return false if the requested category does not exist
    */
    var raw_input_tags = $('#cur_interface_it_' + rec_interface.id).val().replace(/\n/g, " ");;
    var parsed_input_tags = raw_input_tags.match(/[^ ]+/g)
    var input_tags = false;
    if (parsed_input_tags){
        var input_tags = parsed_input_tags.join(',');
    }

    if (input_tags){
        var recommendation_key = input_tags
        if (recommendation_key != CURRENT_RECOMMENDATION_KEY){
            $.ajax({
                type: 'POST',
                url: '/tagrecommendation/get_recommendation/',
                contentType:"application/x-www-form-urlencoded",
                data: {
                    input_tags: input_tags,
                },
                success: function(data) {
                    var parsed_data = JSON.parse(data);
                    var recommendations = parsed_data.tags;
                    var audio_category = parsed_data.audio_category;
                    CURRENT_RECOMMENDATION = recommendations;
                    CURRENT_RECOMMENDATION_KEY = recommendation_key;
                    CURRENT_AUDIO_CATEGORY = audio_category;
                    log('RecommendationForInputTags::' + rec_interface.get_input_tags() + '|withRecommendedTags::' + recommendations.join(','));
                    rec_interface.draw_recommended_tags(recommendations, audio_category);
                }
            });
        } else {
            rec_interface.draw_recommended_tags(CURRENT_RECOMMENDATION);
        }
    } else {
        rec_interface.clear_recommendations();
    }
}