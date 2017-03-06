// Adapted from https://www.w3schools.com/howto/howto_css_modals.asp

function hideModal(){
    $("#fsmodal").hide();
}

function openModal(){
    $("#fsmodal").show();
}

window.onclick = function(event) {
    var modal = $("#fsmodal");
    if (event.target == modal) {
        hideModal();
    }
};

function generateModalHTML(title, contents){
    return '<div id="fsmodal" class="modal"><div class="modal-content"><div class="modal-header"><span onclick="hideModal();" class="close">&times;</span>'
        + title + '</div><div class="modal-body">' + contents + '</div></div></div>';
}

function createAndOpenModal(title, contents){
    $("#fsmodal").remove(); // Delete existing modal
    var modal_html = generateModalHTML(title, contents);
    $("body").prepend(modal_html);
    openModal();
}
