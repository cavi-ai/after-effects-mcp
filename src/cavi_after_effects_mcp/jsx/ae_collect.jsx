$.evalFile(new File(CAVI_LIB));

// list: the footage files in use; relink: item.replace by item id with the copied files.
(function () {
    var a = CAVI_ARGS, i, item, list = [], done = 0, missing = 0, target, j;
    if (a.mode === "list") {
        for (i = 1; i <= app.project.numItems; i++) {
            item = app.project.item(i);
            if (!(item instanceof FootageItem) || item.name === "cavi-report") { continue; }
            if (item.mainSource instanceof SolidSource || !item.mainSource.file) { continue; }
            list.push({id: item.id, name: item.name, file: item.mainSource.file.fsName, used: item.usedIn.length > 0,
                missing: item.footageMissing === true, sequence: !item.mainSource.isStill && /\[\d+-\d+\]/.test(item.name)});
        }
        caviReport({items: list, errors: []});
        return;
    }
    for (j = 0; j < a.links.length; j++) {
        for (i = 1; i <= app.project.numItems; i++) {
            item = app.project.item(i);
            if (item.id === a.links[j].id) {
                item.replace(new File(a.links[j].file));
                done++;
            }
        }
    }
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof FootageItem && item.footageMissing === true) { missing++; }
    }
    caviReport({relinked: done, missing: missing, errors: []});
})();
