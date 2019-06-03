// Freesound Survey 2017 cookies and related
function setSurveyVisited(num_days){
    $.cookie("surveyVisited", "yes", {expires: num_days, path: '/'});
}

function openSurveyPage(){
    // Change the URL here to point to wherever the survey bannder should point to
    window.open('https://freesound.org/forum/freesound-project/41697/', '_blank');
}

function isSurveyVisited(){
    return $.cookie("surveyVisited") == "yes"
}

$(document).ready(function() {
    if (!isSurveyVisited()) {
        showFooterBanner();
    }
});
