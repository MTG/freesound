import { getCookie } from "../utils/cookies";

var queue = Array();
var csrftoken = getCookie('csrftoken');

// the list of files to upload shouldn't have duplicates, use this method with reduce() to ensure it
var removeDuplicates = function removeDuplicates(queue, currentFile) {
    var isSameFile = function isSameFile(file) {
    return file.size === currentFile.size && file.name === currentFile.name;
    };
    var isSoundInSoundsQueue = !!queue.filter(isSameFile).length;
    if (!isSoundInSoundsQueue) {
    return queue.concat(currentFile);
    } else {
    return queue;
    }
};

var trimSize = function trimSize(queue, currentFile) {
    var total_size = queue.reduce((acc, curr) => acc + curr.size, 0);
    if (total_size + currentFile.size < maxUploadSize) {
    return queue.concat(currentFile);
    } else {
    return queue;
    }
};

var setSizeBarValue = function setSizeBarValue(value) {
    var file_size = document.getElementById('file-size');
    file_size.style.width = value + "%";
    if (value >= 0 && value <= 70) {
    file_size.style.background = "green";
    } else if (value > 70 && value <= 90) {
    file_size.style.background = "orange";
    } else {
    file_size.style.background = "red";
    }
    file_size.style.color = "white";
    file_size.innerText = Math.round(maxUploadSize/1024/1024 * (1 - value/100)) + " MB remaining";

    var file_size_bar = document.getElementById('size-table');
    file_size_bar.style.display = (value > 50 ? "inline-table" : "none" );
}

var addSizeBarElement = function addSizeBarElement() {
    var form = fileList.parentNode;
    const sizeTable = document.createElement('table');
    sizeTable.id = "size-table";
    sizeTable.style.width = "100%";
    sizeTable.style.display = "none";
    sizeTable.innerHTML = '<td width=0%; id="file-size"; style="background: #cacad4" /><td style="background: #cacad4" />';
    form.insertBefore(sizeTable, progressContainer);
    return errorList;
};

// add new (or 'dropped') files to the list of files to upload, avoiding duplicates
var onFileInputChange = function onFileInputChange(event) {
    event.preventDefault();
    dropArea.style.display = 'none';  // hide red borders shown while dragging
    var receivedFiles = event.target.files || event.dataTransfer.files;
    for (var i = 0; i < receivedFiles.length; i++) {
    soundsQueue.push(receivedFiles[i]);
    }
    soundsQueue = soundsQueue.reduce(removeDuplicates, []);
    var num = soundsQueue.length;
    soundsQueue = soundsQueue.reduce(trimSize, []);
    num -= soundsQueue.length;
    showListOfSounds();
    var percent_size = soundsQueue.reduce((acc, curr) => acc + curr.size, 0) * 100 / maxUploadSize;
    setSizeBarValue(percent_size);
    resetForm(num > 0 ? "Upload limit of " + maxUploadSizeInMB + " MB exceeded. " + num + " file" + (num > 1 ? "s" : "") + " discarded." : " ");
};

var addErrorListElement = function addErrorListElement() {
    var form = fileList.parentNode;
    var errorList = document.createElement('ul');
    errorList.className = 'errorlist';
    form.insertBefore(errorList, fileList);
    return errorList;
};

var showListOfSounds = function showListOfSounds() {
    fileList.innerHTML = '';
    if (!!dragTip) {
    if (!!soundsQueue.length) {
        dragTip.style.display = 'none';
    } else {
        dragTip.style.display = 'block';
    }
    }
    soundsQueue.forEach(function(soundFile) {
    var node = document.createElement("li");
    var textNode = document.createTextNode(soundFile.name);
    node.appendChild(textNode);
    fileList.appendChild(node);
    });
};

var onDrag = function onDrag(event) {
    event.stopPropagation();
    event.preventDefault();
    dropArea.style.display = 'block';
};

// function to reset form to its initial look (displaying an error message if necessary)
var resetForm = function resetForm(error) {
    // remove progress bar
    progressContainer.innerHTML = '';
    progressContainer.style.display = 'none';
    // reset buttons look
    uploadButton.disabled = false;
    addFilesButton.disabled = false;
    abortButton.style.display = 'none';
    showListOfSounds();
    if (!!error) {
    errorList.innerHTML = '';
    var node = document.createElement("li");
    var textNode = document.createTextNode(error);
    node.appendChild(textNode);
    errorList.appendChild(node);
    }
};

var soundsQueue = [];  // the files we will upload
var submitForm = function submitForm(event) {
    event.preventDefault();
    uploadButton.disabled = true;
    addFilesButton.disabled = true;
    abortButton.style.display = 'inline-block';
    var formData = new FormData();
    soundsQueue.forEach(function addSound(sound) {
    formData.append('files', sound);
    });
    formData.append('csrfmiddlewaretoken', csrftoken);
    var submitURL = uploadForm.dataset.uploadUrl;
    var request = new XMLHttpRequest();
    request.open("POST", submitURL);
    request.onload = function() {
    if (request.status >= 200 && request.status < 400) {  // SUCCESS
        // TODO: consider returning a JSON response to avoid using document.write
        document.open();
        document.write(request.response);
        document.close();
    } else {  // FAILURE
        var errorMessage = 'Something went wrong';
        resetForm(errorMessage);
    }
    };
    request.onerror = function() {
    var errorMessage = 'Something went wrong';
    resetForm(errorMessage);
    };
    request.onabort = function() {
    var errorMessage = 'Upload aborted';
    resetForm(errorMessage);
    };
    // create and fill the progress bar while uploading
    request.upload.onprogress = function updateProgress(event) {
    // function for creating the progress bar
    var addProgressBar = function() {
        var progressNode = document.createElement('div');
        progressNode.className = 'progress';
        progressContainer.appendChild(progressNode);
        return progressNode;
    };
    var progress = (event.lengthComputable) ? event.loaded / event.total : 0;
    progressContainer.style.display = 'inline-block';
    // add the progress bar if not there already
    var progressNode = progressContainer.firstElementChild || addProgressBar();
    // change its width to show the progress update
    progressNode.style.width = progress * 100 + '%';
    if (progress === 1) {
        progressNode.className = 'progress-done';
    }
    };
    abortButton.onclick = function() {
    request.abort();
    };
    request.send(formData);
};

var uploadForm = document.getElementById('upload-form');
uploadForm.onsubmit = submitForm;
var fileInput = document.getElementById('id_files');
var fileList = document.getElementById('file-list');
var addFilesButton = document.getElementById('add-files-btn');
var uploadButton = document.getElementById('html_upload_button');
var progressContainer = document.getElementById('progress-container');
var dragTip = document.getElementById('drag-tip');
var dropArea = document.getElementById('drop-area');
var abortButton = document.getElementById('abort');
var errorList = document.getElementsByClassName('errorlist')[0] || addErrorListElement();
var sizeBar = document.getElementsByClassName('sizebar')[0] || addSizeBarElement();
addFilesButton.onclick = function onclick() { fileInput.click(); };
fileInput.onchange = onFileInputChange;
fileInput.style.display = 'none';
progressContainer.style.display = 'none';
abortButton.style.display = 'none';
var maxUploadSize = uploadForm.dataset.maxFileSize;
var maxUploadSizeInMB = uploadForm.dataset.maxFileSizeMb;

// drag and drop
document.addEventListener('dragenter', onDrag);
document.addEventListener('dragover', function(e) {e.preventDefault();});
document.addEventListener('dragleave', onDrag);
document.addEventListener('drop', onFileInputChange);
