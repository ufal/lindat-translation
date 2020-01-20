def get_or_create(aDict, key, default=lambda: []):
    arr = aDict.get(key, default())
    aDict[key] = arr
    return arr


