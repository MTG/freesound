// Freesound Survey 2017 cookies and related
function setSurveyVisited(num_days){
    $.cookie("surveyVisited", "yes", {expires: num_days, path: '/'});
}

function openSurveyPage(){
    window.open('https://docs.google.com/forms/d/e/1FAIpQLSfO7NFjVwwNaIfl4J95tlz10Oz-_Vc1IEbPpFqAkPV33TeqEw/viewform', '_blank');
}

function isSurveyVisited(){
    return $.cookie("surveyVisited") == "yes"
}

$(document).ready(function() {
    if (!isSurveyVisited()) {
        showFooterBanner();
    }
});
