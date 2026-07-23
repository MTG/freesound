import { initializeObjectSelector } from '../components/objectSelector';
import { activateModal } from '../components/modal';

const editSelectedSoundsButton = document.getElementById('edit-button');
if (editSelectedSoundsButton !== null) {
  editSelectedSoundsButton.disabled = true;
}

const editSelectedPacksButton = document.getElementById('edit-packs-button');
if (editSelectedPacksButton !== null) {
  editSelectedPacksButton.disabled = true;
}

const removeSelectedItemsButton = document.getElementById('remove-button');
if (removeSelectedItemsButton !== null) {
  removeSelectedItemsButton.disabled = true;
}

const reprocessSelectedSoundsButton =
  document.getElementById('reprocess-button');
if (reprocessSelectedSoundsButton !== null) {
  reprocessSelectedSoundsButton.disabled = true;
}

const describeSelectedSoundsButton = document.getElementById('describe-button');
if (describeSelectedSoundsButton !== null) {
  describeSelectedSoundsButton.disabled = true;
}

const objectSelector = [
  ...document.getElementsByClassName('bw-object-selector-container'),
];
objectSelector.forEach(selectorElement => {
  initializeObjectSelector(selectorElement, element => {
    if (editSelectedSoundsButton !== null) {
      editSelectedSoundsButton.disabled = element.dataset.selectedIds === '';
    }
    if (editSelectedPacksButton !== null) {
      const numSelectedIds =
        element.dataset.selectedIds === ''
          ? 0
          : element.dataset.selectedIds.split(',').length;
      editSelectedPacksButton.disabled = numSelectedIds !== 1;
    }
    if (removeSelectedItemsButton !== null) {
      removeSelectedItemsButton.disabled = element.dataset.selectedIds === '';
    }
    if (reprocessSelectedSoundsButton !== null) {
      reprocessSelectedSoundsButton.disabled =
        element.dataset.selectedIds === '';
    }
    if (describeSelectedSoundsButton !== null) {
      describeSelectedSoundsButton.disabled =
        element.dataset.selectedIds === '';
    }
    const objectIdsInput = document.querySelector('input[name="object-ids"]');
    if (objectIdsInput !== null) {
      objectIdsInput.value = element.dataset.selectedIds;
    }
  });
});

var sortByElement = document.getElementById('sort-by');
if (sortByElement !== null) {
  sortByElement.addEventListener('change', function () {
    sortByElement.closest('form').submit();
  });
}

const describeFileCheckboxesWrapper = document.getElementById(
  'describe-file-checkboxes'
);
const describeFilesForm = document.getElementById('fileform');

const numCheckboxesSelected = describeFileCheckboxes => {
  let numChecked = 0;
  describeFileCheckboxes.forEach(checkboxElement => {
    if (checkboxElement.checked) {
      numChecked += 1;
    }
  });
  return numChecked;
};

const noCheckboxSelected = describeFileCheckboxes => {
  return numCheckboxesSelected(describeFileCheckboxes) === 0;
};

const onCheckboxChanged = (checkboxElement, describeFileCheckboxes) => {
  var optionInFilesForm = describeFilesForm.querySelectorAll(
    'option[value=' + checkboxElement.name + ']'
  )[0];
  if (checkboxElement.checked) {
    optionInFilesForm.selected = true;
  } else {
    optionInFilesForm.selected = false;
  }
  const disabled = noCheckboxSelected(describeFileCheckboxes);
  describeSelectedSoundsButton.disabled = disabled;
  removeSelectedItemsButton.disabled = disabled;
};

if (describeFileCheckboxesWrapper !== null) {
  const describeFileCheckboxes =
    describeFileCheckboxesWrapper.querySelectorAll('input');
  describeFileCheckboxes.forEach(checkboxElement => {
    checkboxElement.addEventListener('change', evt => {
      onCheckboxChanged(checkboxElement, describeFileCheckboxes);
    });
  });
}

if (removeSelectedItemsButton !== null) {
  removeSelectedItemsButton.addEventListener('click', evt => {
    evt.preventDefault();
    const confirmationModalTitle = document.getElementById(
      'confirmationModalTitle'
    );
    const confirmationModalHelpText = document.getElementById(
      'confirmationModalHelpText'
    );
    if (objectSelector.length > 0) {
      // We are either selecting sounds or packs
      const multipleElementsSelected =
        objectSelector[0].dataset.selectedIds.split(',').length > 1;
      if (objectSelector[0].dataset.type == 'packs') {
        if (multipleElementsSelected) {
          confirmationModalTitle.innerText =
            'Are you sure you want to remove these packs?';
          confirmationModalHelpText.innerText =
            'Note that the sounds inside these packs will not be deleted.';
        } else {
          confirmationModalTitle.innerText =
            'Are you sure you want to remove this pack?';
          confirmationModalHelpText.innerText =
            'Note that the sounds inside this pack will not be deleted.';
        }
      } else {
        if (multipleElementsSelected) {
          confirmationModalTitle.innerText =
            'Are you sure you want to remove these sounds?';
        } else {
          confirmationModalTitle.innerText =
            'Are you sure you want to remove this sound?';
        }
        confirmationModalHelpText.innerText =
          'Be aware that this action is irreversible...';
      }
    } else {
      // Pending description tab
      if (
        numCheckboxesSelected(
          describeFileCheckboxesWrapper.querySelectorAll('input')
        ) > 1
      ) {
        confirmationModalTitle.innerText =
          'Are you sure you want to remove these sound files?';
      } else {
        confirmationModalTitle.innerText =
          'Are you sure you want to remove this sound file?';
      }
      confirmationModalHelpText.innerText =
        'Be aware that this action is irreversible...';
    }
    const confirmationModalAcceptForm = document.getElementById(
      'confirmationModalAcceptSubmitForm'
    );
    const confirmationModalAcceptButton =
      confirmationModalAcceptForm.querySelectorAll('button')[0];
    confirmationModalAcceptButton.addEventListener('click', evt => {
      evt.preventDefault();
      const removeSelectedItemsButton = document.getElementById(
        'remove-button-hidden'
      );
      removeSelectedItemsButton.click(); // This will trigger submitting the form with the name of the button in it and without submit being intercepted
    });
    activateModal('confirmationModal');
  });
}

const bulkDescribeButton = document.getElementById('bulk-describe-button');
if (bulkDescribeButton !== null) {
  bulkDescribeButton.addEventListener('click', evt => {
    evt.preventDefault();
    activateModal('bulkDescribeModal');
  });
  if (bulkDescribeButton.dataset.formHasErrors !== undefined) {
    activateModal('bulkDescribeModal');
  }
}

const selectAllButton = document.getElementById('select-all');
if (selectAllButton !== null) {
  selectAllButton.addEventListener('click', evt => {
    const describeFileCheckboxes =
      describeFileCheckboxesWrapper.querySelectorAll('input');
    describeFileCheckboxes.forEach(checkboxElement => {
      checkboxElement.checked = true;
      onCheckboxChanged(checkboxElement, describeFileCheckboxes);
    });
  });
}

const selectNoneButton = document.getElementById('select-none');
if (selectNoneButton !== null) {
  selectNoneButton.addEventListener('click', evt => {
    const describeFileCheckboxes =
      describeFileCheckboxesWrapper.querySelectorAll('input');
    describeFileCheckboxes.forEach(checkboxElement => {
      checkboxElement.checked = false;
      onCheckboxChanged(checkboxElement, describeFileCheckboxes);
    });
  });
}
