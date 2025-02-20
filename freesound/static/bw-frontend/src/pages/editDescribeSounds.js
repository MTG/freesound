import {prepareTagsFormFields, updateTags} from "../components/tagsFormField"
import {prepareGeotagFormFields} from "../components/geotagFormField"
import {preparePackFormFields} from "../components/packFormField"
import {prepareAddSoundsModalAndFields} from "../components/addSoundsModal"
import {prepareCategoryFormFields} from "../components/bstCategoryFormField";

prepareAddSoundsModalAndFields(document);
prepareTagsFormFields(document);
preparePackFormFields(document);
prepareCategoryFormFields(document);
document.addEventListener("DOMContentLoaded", () => {
    // Running this inside DOMContentLoaded to make sure mapbox gl scripts are loaded
    prepareGeotagFormFields(document);


});

// Before submitting the form, check if there are any tags that were not properly "updated" and are still pending to be added
var formElement = document.getElementById('edit_describe_form');
var inputTypeSubmitElements = formElement.querySelectorAll('button[type="submit"]');
inputTypeSubmitElements.forEach(button => {
    button.addEventListener("click", (e) => {
        const tagsInputFields = formElement.getElementsByClassName('tags-field');
        tagsInputFields.forEach(tagsFieldElement => {
            const inputElement = tagsFieldElement.getElementsByClassName('tags-input')[0];
            if (inputElement.value) {
                const newTagsStr = inputElement.value;
                inputElement.value = '';
                updateTags(inputElement, newTagsStr);
            }
        });
    });
});

// Move json for BST category field in description form here
