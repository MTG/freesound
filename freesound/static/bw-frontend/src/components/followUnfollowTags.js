import {makePostRequest} from "../utils/postRequest";
import {showToast} from "./toast";

const unfollowText = `Unfollow this tag`;
const followText = `Follow this tag`;
const unfollowTextPlural = `Unfollow these tags`;
const followTextPlural = `Follow these tags`;

const followTags = (tags, button) => {
    const url = button.dataset.followTagsUrl;
    button.disabled = true;
    makePostRequest(url, {}, (responseText) => {        
        button.disabled = false;
        if (responseText.indexOf('Log in to Freesound') == -1){
            // Tags followed successfully, show feedback
            button.innerText = tags.length > 1 ? unfollowTextPlural: unfollowText;
            button.classList.remove('btn-inverse');
            button.classList.add('btn-secondary');
            showToast(`Started following tag(s): ${tags.join(', ')}`);
        } else {
            showToast(`You need to log in before following any tag(s)`);
        }        
    }, () => {
        // Unexpected errors happened while processing request: show errors
        showToast('Some errors occurred while following tags');
    });
}

const unfollowTags = (tags, button) => {
    const url = button.dataset.unfollowTagsUrl;
    button.disabled = true;
    makePostRequest(url, {}, (responseText) => {
        button.disabled = false;
        if (responseText.indexOf('Log in to Freesound') == -1){
        // Tags followed successfully, show feedback
            button.innerText = tags.length > 1 ? followTextPlural: followText;
            button.classList.remove('btn-secondary');
            button.classList.add('btn-inverse');
            showToast(`Stopped following tag(s): ${tags.join(', ')}`);
        } else {
            showToast(`You need to log in before following any tag(s)`);
        }      
    }, () => {
        // Unexpected errors happened while processing request: show errors
        showToast('Some errors occurred while unfollowing tags');
    });
}

const followOrUnFollowTags = (tags, button) => {
    if (button.innerText.indexOf('Unfollow') > -1){
        unfollowTags(tags, button);
    } else {
        followTags(tags, button);
    }
}

const followUnfollowButtons = document.getElementsByClassName('follow-tags-button');
followUnfollowButtons.forEach((button) => {
    const tags = button.dataset.followTagsUrl.split('/follow/follow_tags/')[1].split('/').filter(n => n);
    if (tags.length > 1){
        button.innerText = button.dataset.initialShouldUnfollow === 'true' ? unfollowTextPlural: followTextPlural;
    } else {
        button.innerText = button.dataset.initialShouldUnfollow === 'true' ? unfollowText: followText;
    }
    button.classList.add(button.dataset.initialShouldUnfollow === 'true' ? 'btn-secondary': 'btn-inverse');
    button.addEventListener('click', () => {
        followOrUnFollowTags(tags, button);
    })
});
