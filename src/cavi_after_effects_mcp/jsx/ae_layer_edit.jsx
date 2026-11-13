$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layers = [], i, j, made = [], indices = [], target, copy, result, moved, end;
    for (i = 0; i < a.layers.length; i++) {
        layers.push(caviLayer(comp, a.layers[i]));
    }
    if (a.action === "duplicate") {
        for (i = 0; i < layers.length; i++) {
            copy = layers[i].duplicate();
            if (a.name !== null && layers.length === 1) { copy.name = a.name; }
            made.push(copy);
        }
    } else if (a.action === "delete") {
        for (i = 0; i < layers.length; i++) { made.push(layers[i].name); }
        for (i = 0; i < layers.length; i++) { layers[i].remove(); }
    } else if (a.action === "reorder") {
        for (i = 0; i < layers.length; i++) {
            if (a.move_to === "top") {
                layers[i].moveToBeginning();
            } else if (a.move_to === "bottom") {
                layers[i].moveToEnd();
            } else {
                target = Math.min(Math.max(1, a.move_to + i), comp.numLayers);
                if (target < layers[i].index) { layers[i].moveBefore(comp.layer(target)); } else { layers[i].moveAfter(comp.layer(target)); }
            }
            made.push(layers[i]);
        }
    } else if (a.action === "split") {
        for (i = 0; i < layers.length; i++) {
            if (a.time <= layers[i].inPoint || a.time >= layers[i].outPoint) {
                caviFail("Split time " + a.time + " is outside layer " + layers[i].name + " (" + layers[i].inPoint +
                    " to " + layers[i].outPoint + ")");
            }
            end = layers[i].outPoint;
            copy = layers[i].duplicate();
            layers[i].outPoint = a.time;
            copy.inPoint = a.time;
            copy.outPoint = end;
            made.push(layers[i]);
            made.push(copy);
        }
    } else if (a.action === "precompose") {
        for (i = 0; i < layers.length; i++) { indices.push(layers[i].index); }
        result = comp.layers.precompose(indices, a.name, true);
        made.push(comp.layer(caviPrecompIndex(comp, result.name)));
    } else {
        caviFail("Unknown action " + a.action);
    }
    moved = [];
    for (j = 0; j < made.length; j++) {
        moved.push(typeof made[j] === "string" ? made[j] : describeLayer(made[j]));
    }
    caviReport({comp: comp.name, action: a.action, layers: moved, layer_count: comp.numLayers, errors: []});
})();

function caviPrecompIndex(comp, name) {
    var i;
    for (i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).source && comp.layer(i).source.name === name) { return i; }
    }
    return 1;
}
