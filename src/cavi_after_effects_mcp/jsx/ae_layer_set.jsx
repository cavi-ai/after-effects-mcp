$.evalFile(new File(CAVI_LIB));

var ORIENT = {off: AutoOrientType.NO_AUTO_ORIENT, along_path: AutoOrientType.ALONG_PATH,
    camera_or_poi: AutoOrientType.CAMERA_OR_POINT_OF_INTEREST, toward_camera: AutoOrientType.CHARACTERS_TOWARD_CAMERA};
var QUALITY = {best: LayerQuality.BEST, draft: LayerQuality.DRAFT, wireframe: LayerQuality.WIREFRAME};
var SAMPLING = {bilinear: LayerSamplingQuality.BILINEAR, bicubic: LayerSamplingQuality.BICUBIC};

function nameOf(table, value) {
    var key;
    for (key in table) {
        if (table.hasOwnProperty(key) && table[key] === value) { return key; }
    }
    return String(value);
}

// Text and shape layers are not instances of AVLayer in ExtendScript, so cameras and lights are the exceptions.
function isAV(layer) {
    return !(layer instanceof CameraLayer) && !(layer instanceof LightLayer);
}

// Collapse, guide, quality, sampling and adjustment exist only on AV layers, not on cameras and lights.
function switches(layer, a) {
    var av = ["collapse_transformation", "guide", "quality", "sampling", "adjustment"], i, who = "Layer " + layer.name + " (" + layerType(layer) + ")";
    if (!isAV(layer)) {
        for (i = 0; i < av.length; i++) {
            if (a[av[i]] !== null) { caviFail(who + " has no " + av[i] + " switch"); }
        }
    }
    if (a.collapse_transformation !== null) {
        if (!layer.canSetCollapseTransformation) { caviFail(who + " cannot collapse transformations"); }
        layer.collapseTransformation = a.collapse_transformation;
    }
    if (a.guide !== null) { layer.guideLayer = a.guide; }
    if (a.quality !== null) { layer.quality = QUALITY[a.quality]; }
    if (a.sampling !== null) { layer.samplingQuality = SAMPLING[a.sampling]; }
    if (a.adjustment !== null) { layer.adjustmentLayer = a.adjustment; }
    if (a.auto_orient !== null) {
        if (a.auto_orient === "toward_camera" && !(layer instanceof TextLayer)) {
            caviFail(who + " is not text; toward_camera orients text characters");
        }
        if (a.auto_orient === "camera_or_poi" && isAV(layer) && !layer.threeDLayer) {
            caviFail(who + " is 2D; camera_or_poi needs three_d");
        }
        layer.autoOrient = ORIENT[a.auto_orient];
    }
}

function report(layer) {
    var out = {auto_orient: nameOf(ORIENT, layer.autoOrient)};
    if (isAV(layer)) {
        out.collapse_transformation = layer.collapseTransformation;
        out.guide = layer.guideLayer;
        out.quality = nameOf(QUALITY, layer.quality);
        out.sampling = nameOf(SAMPLING, layer.samplingQuality);
        out.adjustment = layer.adjustmentLayer;
    }
    return out;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), path, applied = [], values = {}, matte, prop, parent;
    // A locked layer refuses every other change, so unlock first and lock last.
    if (a.locked === false) { layer.locked = false; }
    if (a.three_d !== null) { layer.threeDLayer = a.three_d; }
    if (a.motion_blur !== null) {
        if (a.motion_blur && layer instanceof ShapeLayer) { caviGuard3D(comp, layer, "motion blur"); }
        layer.motionBlur = a.motion_blur;
    }
    if (a.name !== null) { layer.name = a.name; }
    if (a.enabled !== null) { layer.enabled = a.enabled; }
    if (a.solo !== null) { layer.solo = a.solo; }
    if (a.shy !== null) { layer.shy = a.shy; }
    if (a.label !== null) { layer.label = a.label; }
    if (a.stretch !== null) { layer.stretch = a.stretch; }
    if (a.start_time !== null) { layer.startTime = a.start_time; }
    if (a.in_point !== null) { layer.inPoint = a.in_point; }
    if (a.out_point !== null) { layer.outPoint = a.out_point; }
    if (a.blend_mode !== null) { layer.blendingMode = caviEnum(BlendingMode, a.blend_mode, "blend mode"); }
    switches(layer, a);
    if (a.no_parent) {
        layer.parent = null;
    } else if (a.parent !== null) {
        parent = caviLayer(comp, a.parent);
        layer.parent = parent;
    }
    if (a.track_matte === "none") {
        layer.removeTrackMatte();
    } else if (a.track_matte !== null) {
        matte = a.track_matte;
        layer.setTrackMatte(caviLayer(comp, matte.layer), caviEnum(TrackMatteType, matte.type, "track matte type"));
    }
    for (path in a.properties) {
        if (a.properties.hasOwnProperty(path)) {
            prop = caviProp(layer, path);
            caviSetStatic(prop, a.properties[path]);
            applied.push(path);
            values[path] = prop.value;
        }
    }
    if (a.locked === true) { layer.locked = true; }
    caviReport({comp: comp.name, layer: describeLayer(layer), properties_set: applied, values: values, solo: layer.solo, shy: layer.shy,
        locked: layer.locked, label: layer.label, stretch: layer.stretch, start_time: layer.startTime,
        blend_mode: String(layer.blendingMode), motion_blur: layer.motionBlur, switches: report(layer), errors: []});
})();
