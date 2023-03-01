import {prepareSourcesFormFields} from "../components/sourcesFormField"
import {prepareTagsFormFields} from "../components/tagsFormField"
import {prepareGeotagFormFields} from "../components/geotagFormField"
import {preparePackFormFields} from "../components/packFormField"


prepareSourcesFormFields();
prepareTagsFormFields();
preparePackFormFields();
document.addEventListener("DOMContentLoaded", () => {
    // Running this inside DOMContentLoaded to make sure mapbox gl scripts are loaded
    prepareGeotagFormFields();    
});
