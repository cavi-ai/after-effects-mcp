$.evalFile(new File(CAVI_LIB));

function layerType(layer) {
    if (layer instanceof CameraLayer) { return "camera"; }
    if (layer instanceof LightLayer) { return "light"; }
    if (layer instanceof ShapeLayer) { return "shape"; }
    if (layer instanceof TextLayer) { return "text"; }
    if (layer.nullLayer) { return "null"; }
    if (layer.adjustmentLayer) { return "adjustment"; }
    if (layer.source instanceof CompItem) { return "comp"; }
    if (layer.source && layer.source.mainSource instanceof SolidSource) { return "solid"; }
    return "footage";
}

// Properties with keyframes, as path strings, found by walking the layer's property tree.
function keyed(group, path, found) {
    var i, prop;
    for (i = 1; i <= group.numProperties; i++) {
        prop = group.property(i);
        if (prop.propertyType === PropertyType.PROPERTY) {
            if (prop.numKeys > 0) {
                found.push({path: path + prop.matchName, name: prop.name, keys: prop.numKeys});
            }
        } else {
            keyed(prop, path + prop.matchName + "/", found);
        }
    }
}

function describeLayer(layer) {
    var effects = [], parade = layer.property("ADBE Effect Parade"), i, found = [];
    if (parade) {
        for (i = 1; i <= parade.numProperties; i++) {
            effects.push({name: parade.property(i).name, match_name: parade.property(i).matchName});
        }
    }
    keyed(layer, "", found);
    return {index: layer.index, name: layer.name, type: layerType(layer), in_point: layer.inPoint,
        out_point: layer.outPoint, three_d: layer.threeDLayer === true, parent: layer.parent ? layer.parent.name : null,
        enabled: layer.enabled, effects: effects, keyframed: found};
}

(function () {
    var scope = CAVI_ARGS.scope, report = {scope: scope, errors: []}, i, item, comp, queue, list;
    if (scope === "project") {
        report.comps = []; report.footage = []; report.folders = [];
        for (i = 1; i <= app.project.numItems; i++) {
            item = app.project.item(i);
            if (item.name === "cavi-report") { continue; }
            if (item instanceof CompItem) {
                report.comps.push({name: item.name, width: item.width, height: item.height, duration: item.duration,
                    fps: item.frameRate, layers: item.numLayers, renderer: item.renderer});
            } else if (item instanceof FolderItem) {
                report.folders.push({name: item.name, items: item.numItems});
            } else {
                report.footage.push({name: item.name, file: item.mainSource.file ? item.mainSource.file.fsName : null,
                    missing: item.footageMissing === true, width: item.width, height: item.height, duration: item.duration,
                    solid: item.mainSource instanceof SolidSource});
            }
        }
    } else if (scope === "comp") {
        comp = caviComp(CAVI_ARGS.comp);
        report.comp = comp.name; report.renderer = comp.renderer; report.layers = [];
        for (i = 1; i <= comp.numLayers; i++) {
            report.layers.push(describeLayer(comp.layer(i)));
        }
    } else {
        queue = app.project.renderQueue;
        list = [];
        for (i = 1; i <= queue.numItems; i++) {
            list.push(caviQueueItem(queue.item(i), i));
        }
        report.queue = list;
    }
    caviReport(report);
})();
