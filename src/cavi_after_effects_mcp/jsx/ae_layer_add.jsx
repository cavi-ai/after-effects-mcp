$.evalFile(new File(CAVI_LIB));

function footageItem(path) {
    var i, item, file = new File(path), options;
    if (!file.exists) {
        caviFail("No footage file at " + path);
    }
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof FootageItem && item.mainSource.file && item.mainSource.file.fsName === file.fsName) {
            return item;
        }
    }
    options = new ImportOptions(file);
    return app.project.importFile(options);
}

function shapeRect(comp, a) {
    var layer = comp.layers.addShape(), contents, w = a.width || comp.width, h = a.height || comp.height, line;
    layer.name = a.name;
    contents = layer.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group").property("ADBE Vectors Group");
    contents.addProperty("ADBE Vector Shape - Rect").property("ADBE Vector Rect Size").setValue([w, h]);
    if (a.stroke) {
        line = contents.addProperty("ADBE Vector Graphic - Stroke");
        line.property("ADBE Vector Stroke Color").setValue(a.stroke);
        line.property("ADBE Vector Stroke Width").setValue(a.stroke_width);
    }
    if (a.fill) {
        contents.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(a.fill);
    }
    return layer;
}

function textLayer(comp, a) {
    var layer = a.box ? comp.layers.addBoxText(a.box, a.text) : comp.layers.addText(a.text), source, doc;
    source = layer.property("ADBE Text Properties").property("ADBE Text Document");
    doc = source.value;
    doc.resetCharStyle();
    doc.resetParagraphStyle();
    doc.applyFill = false;
    doc.applyStroke = false;
    caviTextStyle(doc, a);
    source.setValue(doc);
    return layer;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer, kind = a.kind, item, lights, w, h, rect, fitted = null;
    if (kind === "solid" || kind === "adjustment") {
        w = a.width || comp.width; h = a.height || comp.height;
        layer = comp.layers.addSolid(a.color, a.name, w, h, 1, comp.duration);
        layer.adjustmentLayer = kind === "adjustment";
    } else if (kind === "text") {
        layer = textLayer(comp, a);
    } else if (kind === "footage") {
        item = footageItem(a.file);
        layer = comp.layers.add(item);
    } else if (kind === "comp") {
        if (a.source === comp.name) { caviFail("A comp cannot contain itself"); }
        layer = comp.layers.add(caviComp(a.source));
    } else if (kind === "model") {
        if (comp.renderer !== "ADBE Calder") {
            caviFail("3D model layers need the Advanced 3D renderer; comp " + comp.name + " uses " + comp.renderer);
        }
        layer = comp.layers.add(footageItem(a.file));
        layer.outPoint = comp.duration;
        if (a.fit) {
            rect = layer.sourceRectAtTime(0, false);
            fitted = 0.6 * comp.height / (Math.max(rect.width, rect.height) * Math.sqrt(3)) * 100;
            layer.property("ADBE Transform Group").property("ADBE Position").setValue([comp.width / 2, comp.height / 2, 0]);
            layer.property("ADBE Transform Group").property("ADBE Scale").setValue([fitted, fitted, fitted]);
        }
    } else if (kind === "shape_rect") {
        layer = shapeRect(comp, a);
    } else if (kind === "null") {
        layer = comp.layers.addNull(comp.duration);
    } else if (kind === "camera") {
        layer = comp.layers.addCamera(a.name, a.position ? [a.position[0], a.position[1]] : [comp.width / 2, comp.height / 2]);
    } else if (kind === "light") {
        lights = {POINT: LightType.POINT, SPOT: LightType.SPOT, PARALLEL: LightType.PARALLEL, AMBIENT: LightType.AMBIENT,
            ENVIRONMENT: LightType.ENVIRONMENT};
        layer = comp.layers.addLight(a.name, [comp.width / 2, comp.height / 2]);
        layer.lightType = caviEnum(lights, a.light_type, "light type");
    } else {
        caviFail("Unknown layer kind " + kind);
    }
    layer.name = a.name;
    if (a.three_d && !layer.threeDLayer) { layer.threeDLayer = true; }
    if (a.start_time !== null) { layer.startTime = a.start_time; }
    if (a.in_point !== null) { layer.inPoint = a.in_point; }
    if (a.out_point !== null) { layer.outPoint = a.out_point; }
    caviTransform(layer, a.transform);
    if (a.blend_mode) { layer.blendingMode = caviEnum(BlendingMode, a.blend_mode, "blend mode"); }
    if (a.motion_blur) {
        if (kind === "shape_rect") { caviGuard3D(comp, layer, "motion blur"); }
        layer.motionBlur = true;
    }
    if (a.parent !== null) { layer.parent = caviLayer(comp, a.parent); }
    if (a.track_matte) {
        layer.setTrackMatte(caviLayer(comp, a.track_matte.layer),
            caviEnum(TrackMatteType, a.track_matte.type, "track matte type"));
    }
    caviReport({comp: comp.name, layer: {index: layer.index, name: layer.name, kind: kind, three_d: caviIs3D(layer),
        in_point: layer.inPoint, out_point: layer.outPoint, parent: layer.parent ? layer.parent.name : null, fit_scale: fitted},
        errors: []});
})();
