$.evalFile(new File(CAVI_LIB));

function footageItem(path) {
    var i, item, file = new File(path);
    if (!file.exists) { caviFail("No footage file at " + path); }
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof FootageItem && item.mainSource.file && item.mainSource.file.fsName === file.fsName) {
            return item;
        }
    }
    return app.project.importFile(new ImportOptions(file));
}

// Moves each layer so it starts where the previous one ends minus the overlap; earlier layers end up above later ones.
(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), t = a.start, layers = [], joins = [], i, item, layer, length, prev;
    for (i = 0; i < a.items.length; i++) {
        item = a.items[i];
        layer = item.layer !== null ? caviLayer(comp, item.layer) : comp.layers.add(footageItem(item.file));
        if (item.layer === null) { layer.name = layer.name + " " + (i + 1); }
        length = item.duration !== null ? item.duration : layer.outPoint - layer.inPoint;
        if (length <= a.overlap && i < a.items.length - 1) {
            caviFail("Item " + (i + 1) + " is " + length + " s long, not longer than the overlap " + a.overlap);
        }
        if (t + length > comp.duration + 0.0001) {
            caviFail("Item " + (i + 1) + " ends at " + (t + length) + " s, past the comp duration " + comp.duration);
        }
        layer.startTime = layer.startTime + (t - layer.inPoint);
        layer.outPoint = layer.inPoint + length;
        layers.push(layer);
        if (prev) { joins.push({from_layer: prev.name, to_layer: layer.name, at: layer.inPoint}); }
        prev = layer;
        t = t + length - a.overlap;
    }
    for (i = layers.length - 1; i >= 0; i--) { layers[i].moveToBeginning(); }
    caviReport({comp: comp.name, layers: describeAll(layers), joins: joins, errors: []});
})();

function describeAll(layers) {
    var i, out = [];
    for (i = 0; i < layers.length; i++) {
        out.push({index: layers[i].index, name: layers[i].name, in_point: layers[i].inPoint, out_point: layers[i].outPoint});
    }
    return out;
}
