$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, file = new File(a.file), i, item, target = null, before, used = 0, j, comp;
    if (!file.exists) {
        caviFail("No file at " + a.file);
    }
    for (i = 1; i <= app.project.numItems && !target; i++) {
        item = app.project.item(i);
        if (item instanceof FootageItem && item.name === a.item) {
            target = item;
        }
    }
    if (!target) {
        caviFail("No footage item named " + a.item);
    }
    before = target.mainSource.file ? target.mainSource.file.fsName : null;
    target.replace(file);
    for (i = 1; i <= app.project.numItems; i++) {
        comp = app.project.item(i);
        if (comp instanceof CompItem) {
            for (j = 1; j <= comp.numLayers; j++) {
                if (comp.layer(j).source === target) { used++; }
            }
        }
    }
    caviReport({item: target.name, previous: before, file: target.mainSource.file.fsName,
        missing: target.footageMissing === true, layers_using: used, errors: []});
})();
