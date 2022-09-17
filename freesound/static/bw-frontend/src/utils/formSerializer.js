// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const serialize = function(formEle) {
    // Code exceprt adapted from https://htmldom.dev/serialize-form-data-into-a-query-string/

    // Get all fields
    const fields = [].slice.call(formEle.elements, 0);
    return fields
        .map(function(ele) {
            const name = ele.name;
            const type = ele.type;

            // We ignore
            // - field that doesn't have a name
            // - disabled field
            // - `file` input
            // - unselected checkbox/radio
            if (!name ||
                ele.disabled ||
                type === 'file' ||
                (/(checkbox|radio)/.test(type) && !ele.checked))
            {
                return '';
            }

            // Multiple select
            if (type === 'select-multiple') {
                return ele.options
                    .map(function(opt) {
                        return opt.selected
                            ? `${encodeURIComponent(name)}=${encodeURIComponent(opt.value)}`
                            : '';
                    })
                    .filter(function(item) {
                        return item;
                    })
                    .join('&');
            }

            return `${encodeURIComponent(name)}=${encodeURIComponent(ele.value)}`;
        })
        .filter(function(item) {
            return item;
        })
        .join('&');
};

export default serialize;

// @license-end
