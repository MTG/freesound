const serializedIdListToIntList = value =>
    value ? value.split(',').map(s => parseInt(s, 10)) : [];

const combineIdsLists = (list1, list2) => [...new Set([...list1, ...list2])];

export { serializedIdListToIntList, combineIdsLists };