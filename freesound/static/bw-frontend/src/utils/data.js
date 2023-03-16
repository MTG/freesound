const serializedIdListToIntList = serializedIdList => {
    const outputList = [];
    if (serializedIdList !== '' && serializedIdList !== undefined){
        serializedIdList.split(',').forEach(splitPart => {
            outputList.push(parseInt(splitPart, 10));
        });
    }
    return outputList;
}

const combineIdsLists = (list1, list2) => {
    const outputList = [];
    list1.forEach(listItem => {
        if (outputList.indexOf(listItem) == -1){
            outputList.push(listItem);
        }
    });
    list2.forEach(listItem => {
        if (outputList.indexOf(listItem) == -1){
            outputList.push(listItem);
        }
    });
    return outputList;
}

export {serializedIdListToIntList, combineIdsLists};