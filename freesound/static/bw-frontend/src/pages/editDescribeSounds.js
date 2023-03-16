import {prepareTagsFormFields} from "../components/tagsFormField"
import {prepareGeotagFormFields} from "../components/geotagFormField"
import {preparePackFormFields} from "../components/packFormField"
import {prepareAddSoundsModalAndFields} from "../components/addSoundsModal"

prepareAddSoundsModalAndFields();
prepareTagsFormFields();
preparePackFormFields();
document.addEventListener("DOMContentLoaded", () => {
    // Running this inside DOMContentLoaded to make sure mapbox gl scripts are loaded
    prepareGeotagFormFields();    
});
