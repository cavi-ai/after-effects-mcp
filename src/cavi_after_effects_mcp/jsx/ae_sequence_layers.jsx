$.evalFile(new File(CAVI_LIB));

// Moves each layer so it starts where the previous one ends minus the overlap; earlier layers end up above later ones.
(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), t = a.start, layers = [], joins = [], i, item, layer, length, prev;
    for (i = 0; i < a.items.length; i++) {
        item = a.items[i];
        layer = item.layer !== null ? caviLayer(comp, item.layer) : comp.layers.add(caviFootage(item.file));
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
        // After Effects ends a layer at the end of its source; a longer duration would leave a gap.
        if (layer.outPoint < layer.inPoint + length - comp.frameDuration / 2) {
            caviFail("Item " + (i + 1) + " has " + (layer.outPoint - layer.inPoint) + " s of source from its in point; "
                + "duration " + length + " s is longer");
        }
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
