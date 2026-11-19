// Helpers shared by the tool templates. ExtendScript is ES3: no JSON, no Array.indexOf.
var CAVI_TRANSFORM = {
    position: "ADBE Position", anchor: "ADBE Anchor Point", scale: "ADBE Scale", rotation: "ADBE Rotate Z",
    rotationx: "ADBE Rotate X", rotationy: "ADBE Rotate Y", orientation: "ADBE Orientation", opacity: "ADBE Opacity"
};

function caviFail(message) {
    throw new Error(message);
}

// The one comp named ``name``; a name two comps share is refused with their item ids.
function caviComp(name) {
    var i, item, found = [], ids = [];
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof CompItem && item.name === name) {
            found.push(item);
            ids.push(item.id);
        }
    }
    if (found.length > 1) {
        caviFail(found.length + " comps are named " + name + " (item ids " + ids.join(", ")
            + "); rename all but one with ae_organize");
    }
    return found.length ? found[0] : caviFail("No comp named " + name);
}

// A layer by index, or the one layer named ``ref``; a name two layers share is refused with their indices.
function caviLayer(comp, ref) {
    var i, found = [];
    if (typeof ref === "number") {
        if (ref < 1 || ref > comp.numLayers) {
            caviFail("Comp " + comp.name + " has no layer " + ref);
        }
        return comp.layer(ref);
    }
    for (i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === ref) {
            found.push(i);
        }
    }
    if (found.length > 1) {
        caviFail("Comp " + comp.name + " has " + found.length + " layers named " + ref + " (indices "
            + found.join(", ") + "); pass the index");
    }
    return found.length ? comp.layer(found[0]) : caviFail("Comp " + comp.name + " has no layer named " + ref);
}

// A property by path: "position", "Transform/Position" or match names, joined with "/".
function caviProp(layer, path) {
    var parts = String(path).split("/"), alias = CAVI_TRANSFORM[String(path).toLowerCase()], prop = layer, i;
    if (alias) {
        parts = ["ADBE Transform Group", alias];
    }
    for (i = 0; i < parts.length; i++) {
        prop = prop.property(parts[i]);
        if (!prop) {
            caviFail("Layer " + layer.name + " has no property " + parts.slice(0, i + 1).join("/"));
        }
    }
    return prop;
}

// Advanced 3D aborts the script uncatchably on an effect on a 3D layer or motion blur on a 3D shape layer.
function caviGuard3D(comp, layer, action) {
    if (comp.renderer === "ADBE Calder" && layer.threeDLayer) {
        caviFail("Refused: " + action + " on 3D layer " + layer.name + " aborts After Effects while comp " +
            comp.name + " uses the Advanced 3D renderer (ADBE Calder)");
    }
}

function caviEnum(table, name, what) {
    var key = String(name).toUpperCase();
    if (table[key] === undefined) {
        caviFail("Unknown " + what + " " + name);
    }
    return table[key];
}

function caviTransform(layer, spec) {
    var key, prop;
    for (key in spec) {
        if (spec.hasOwnProperty(key) && spec[key] !== null && CAVI_TRANSFORM[key]) {
            prop = caviProp(layer, key);
            if (prop.propertyValueType === PropertyValueType.ThreeD_SPATIAL ||
                prop.propertyValueType === PropertyValueType.ThreeD) {
                if (spec[key] instanceof Array && spec[key].length === 2) {
                    spec[key].push(key === "scale" ? 100 : 0);
                }
            }
            prop.setValue(spec[key]);
        }
    }
}

function caviEase(prop, key, ease) {
    var dims = 1, list = [], d;
    if (!prop.isSpatial) {
        if (prop.propertyValueType === PropertyValueType.TwoD) {
            dims = 2;
        } else if (prop.propertyValueType === PropertyValueType.ThreeD) {
            dims = 3;
        }
    }
    for (d = 0; d < dims; d++) {
        list.push(new KeyframeEase(ease.speed, ease.influence));
    }
    return list;
}

// Keys as [{time, value, ease_in, ease_out, interpolation}] at distinct times; the tools refuse a repeated time.
function caviKeys(prop, keys, fallback) {
    var i, k, key, inEase, outEase, kind, kinds = {LINEAR: KeyframeInterpolationType.LINEAR,
        BEZIER: KeyframeInterpolationType.BEZIER, HOLD: KeyframeInterpolationType.HOLD};
    for (i = 0; i < keys.length; i++) {
        prop.setValueAtTime(keys[i].time, caviMenuValue(prop, keys[i].value));
    }
    for (i = 0; i < keys.length; i++) {
        key = keys[i];
        k = prop.nearestKeyIndex(key.time);
        kind = key.interpolation ? String(key.interpolation).toUpperCase() : null;
        if (kind && kind !== "BEZIER") {
            prop.setInterpolationTypeAtKey(k, kinds[kind], kinds[kind]);
            continue;
        }
        inEase = key.ease_in || fallback;
        outEase = key.ease_out || fallback;
        if (inEase || outEase) {
            prop.setTemporalEaseAtKey(k, caviEase(prop, k, inEase || outEase), caviEase(prop, k, outEase || inEase));
        }
    }
}

function caviStatus(item) {
    var names = ["WILL_CONTINUE", "NEEDS_OUTPUT", "UNQUEUED", "QUEUED", "RENDERING", "USER_STOPPED", "ERR_STOPPED",
        "DONE"], i;
    for (i = 0; i < names.length; i++) {
        if (RQItemStatus[names[i]] === item.status) {
            return names[i];
        }
    }
    return String(item.status);
}

function caviQueueItem(item, index) {
    var module = item.outputModule(1), i, templates = [];
    for (i = 0; i < module.templates.length; i++) {
        templates.push(module.templates[i]);
    }
    var settings = module.getSettings(GetSettingsFormat.STRING), keys = ["Channels", "Depth", "Color", "Resize", "Resize to",
        "Crop", "Output Audio", "Audio Sample Rate", "Audio Channels"], shown = {}, k;
    for (k = 0; k < keys.length; k++) { shown[keys[k]] = settings[keys[k]]; }
    var rs = item.getSettings(GetSettingsFormat.STRING), rk = ["Quality", "Resolution", "Proxy Use", "Effects", "Motion Blur",
        "Frame Blending", "Frame Rate", "Use this frame rate"], render = {};
    for (k = 0; k < rk.length; k++) { render[rk[k]] = rs[rk[k]]; }
    // As numbers, "Frame Rate" is 0 while the entry uses the comp's rate and "Use this frame rate" holds the rate.
    var rates = item.getSettings(GetSettingsFormat.NUMBER), fps = rates["Frame Rate"] ? rates["Use this frame rate"] : item.comp.frameRate;
    return {index: index, comp: item.comp.name, status: caviStatus(item), render: item.render,
        label: item.comp.label, file: module.file ? module.file.fsName : null,
        output_module: module.name, templates: templates, span_start: item.timeSpanStart,
        span_duration: item.timeSpanDuration, fps: fps, comp_fps: item.comp.frameRate,
        frames: Math.round(item.timeSpanDuration * fps), settings: shown, render_settings: render};
}

// Cameras and lights are always 3D, although threeDLayer reads false for them.
function caviIs3D(layer) {
    return layer.threeDLayer === true || layer instanceof CameraLayer || layer instanceof LightLayer;
}

// One layer as {index, name, type, in/out, 3D, parent, enabled, effects, keyframed paths}.
function layerType(layer) {
    if (layer instanceof CameraLayer) { return "camera"; }
    if (layer instanceof LightLayer) { return "light"; }
    if (layer instanceof ShapeLayer) { return "shape"; }
    if (layer instanceof TextLayer) { return "text"; }
    if (typeof ParametricMeshLayer !== "undefined" && layer instanceof ParametricMeshLayer) { return "mesh"; }
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
        out_point: layer.outPoint, three_d: caviIs3D(layer), parent: layer.parent ? layer.parent.name : null,
        enabled: layer.enabled, effects: effects, keyframed: found};
}

var CAVI_JUSTIFY = {LEFT: ParagraphJustification.LEFT_JUSTIFY, CENTER: ParagraphJustification.CENTER_JUSTIFY,
    RIGHT: ParagraphJustification.RIGHT_JUSTIFY, FULL: ParagraphJustification.FULL_JUSTIFY_LASTLINE_LEFT};

// Applies the TextDocument fields present in s (font, size, fill, stroke, stroke_width, tracking, leading,
// justification, box); fields that are null or absent are left alone.
function caviTextStyle(doc, s) {
    function has(key) { return s[key] !== undefined && s[key] !== null; }
    if (has("font")) {
        if (app.fonts.getFontsByPostScriptName(s.font).length === 0) {
            caviFail("Font " + s.font + " is not installed; ae_fonts lists the PostScript names");
        }
        doc.font = s.font;
    }
    if (has("size")) { doc.fontSize = s.size; }
    if (has("fill")) { doc.applyFill = true; doc.fillColor = s.fill; }
    if (has("stroke")) { doc.applyStroke = true; doc.strokeColor = s.stroke; }
    if (has("stroke_width")) { doc.strokeWidth = s.stroke_width; }
    if (has("tracking")) { doc.tracking = s.tracking; }
    if (has("leading")) { doc.autoLeading = false; doc.leading = s.leading; }
    if (has("justification")) { doc.justification = caviEnum(CAVI_JUSTIFY, s.justification, "justification"); }
    if (has("box")) { doc.boxTextSize = s.box; }
    if (has("box_fit") || has("box_align") || has("box_inset")) {
        if (typeof BoxAutoFitPolicy === "undefined") {
            caviFail("box_fit, box_align and box_inset need After Effects 24.6 or later");
        }
        if (!doc.boxText) {
            caviFail("box_fit, box_align and box_inset apply to paragraph text; this layer is point text");
        }
    }
    // Alignment first: After Effects switches the fit off unless the text sits at the top of its box.
    if (has("box_align")) { doc.boxVerticalAlignment = caviEnum(caviBoxAligns(), s.box_align, "box alignment"); }
    if (has("box_fit")) {
        if (s.box_fit !== "none" && doc.boxVerticalAlignment !== BoxVerticalAlignment.TOP) {
            caviFail("box_fit grows a box only with box_align top; the text is aligned " + caviNameOf(caviBoxAligns(), doc.boxVerticalAlignment));
        }
        doc.boxAutoFitPolicy = caviEnum(caviBoxFits(), s.box_fit, "box fit");
    }
    if (has("box_inset")) { doc.boxInsetSpacing = s.box_inset; }
}

// Built on use: the enums exist only in After Effects 24.6 and later.
function caviBoxFits() {
    return {NONE: BoxAutoFitPolicy.NONE, CURSOR: BoxAutoFitPolicy.HEIGHT_CURSOR,
        BOUNDS: BoxAutoFitPolicy.HEIGHT_PRECISE_BOUNDS, BASELINE: BoxAutoFitPolicy.HEIGHT_BASELINE};
}

function caviBoxAligns() {
    return {TOP: BoxVerticalAlignment.TOP, CENTER: BoxVerticalAlignment.CENTER, BOTTOM: BoxVerticalAlignment.BOTTOM,
        JUSTIFY: BoxVerticalAlignment.JUSTIFY};
}

// The lowercase key of ``value`` in ``table``, or null.
function caviNameOf(table, value) {
    var key;
    for (key in table) {
        if (table[key] === value) { return key.toLowerCase(); }
    }
    return null;
}

// A paragraph box's fit, alignment, inset and overflow as they read back; null for point text or before 24.6.
function caviBoxState(doc) {
    if (!doc.boxText || typeof BoxAutoFitPolicy === "undefined") {
        return {box_fit: null, box_align: null, box_inset: null, overflow: null};
    }
    return {box_fit: caviNameOf(caviBoxFits(), doc.boxAutoFitPolicy), box_align: caviNameOf(caviBoxAligns(), doc.boxVerticalAlignment),
        box_inset: doc.boxInsetSpacing, overflow: doc.boxOverflow};
}

// Sets a static value; text documents belong to ae_text_set and keyed properties to ae_keyframes.
function caviSetStatic(prop, value) {
    if (prop.propertyType !== PropertyType.PROPERTY) {
        caviFail(prop.name + " is a group; give a property path");
    }
    if (prop.propertyValueType === PropertyValueType.TEXT_DOCUMENT) {
        caviFail(prop.name + " is text; use ae_text_set");
    }
    if (prop.numKeys > 0) {
        caviFail(prop.name + " has keyframes; use ae_keyframes");
    }
    if ((prop.propertyValueType === PropertyValueType.ThreeD_SPATIAL ||
        prop.propertyValueType === PropertyValueType.ThreeD) && value instanceof Array && value.length === 2) {
        value.push(prop.matchName === "ADBE Scale" ? 100 : 0);
    }
    prop.setValue(caviMenuValue(prop, value));
}

// A menu property's items, with the "(-" separators that each take an index; null for any other property and
// before After Effects 26.0, where propertyParameters is undefined.
function caviMenuItems(prop) {
    var items;
    try { items = prop.propertyParameters; } catch (notMenu) { return null; }
    return items === undefined ? null : items;
}

// ``value`` with a menu item's text replaced by its 1-based index; other values are returned as they are.
function caviMenuValue(prop, value) {
    var items, i, names = [];
    if (typeof value !== "string") { return value; }
    items = caviMenuItems(prop);
    if (items === null) {
        if (parseFloat(app.version) < 26) { caviFail("Menu items by name need After Effects 26.0 or later; give " + prop.name + " the item's 1-based index"); }
        caviFail(prop.name + " is not a menu; it takes no text " + value);
    }
    for (i = 0; i < items.length; i++) {
        if (items[i] === value && value !== "(-") { return i + 1; }
        if (items[i] !== "(-") { names.push(items[i]); }
    }
    caviFail(prop.name + " has no item " + value + "; its items are " + names.join(", "));
}

// The project folder at path "A/B" from the root, each missing level created.
function caviFolder(path) {
    var parts = path.split("/"), parent = app.project.rootFolder, i, j, child;
    for (i = 0; i < parts.length; i++) {
        child = null;
        for (j = 1; j <= parent.numItems; j++) {
            if (parent.item(j) instanceof FolderItem && parent.item(j).name === parts[i]) { child = parent.item(j); }
        }
        if (!child) {
            child = app.project.items.addFolder(parts[i]);
            child.parentFolder = parent;
        }
        parent = child;
    }
    return parent;
}

// Restyles existing keys: hold, temporal ease, spatial interpolation (bezier or linear) and roving.
function caviRestyle(prop, a) {
    var k, last = prop.numKeys, zero, i;
    for (k = 1; k <= last; k++) {
        if (a.hold) {
            prop.setInterpolationTypeAtKey(k, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD);
        } else if (a.ease) {
            prop.setInterpolationTypeAtKey(k, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
            prop.setTemporalEaseAtKey(k, caviEase(prop, k, a.ease), caviEase(prop, k, a.ease));
        }
        if (a.spatial && prop.isSpatial) {
            if (a.spatial === "linear") {
                zero = [];
                for (i = 0; i < (prop.propertyValueType === PropertyValueType.ThreeD_SPATIAL ? 3 : 2); i++) { zero.push(0); }
                prop.setSpatialTangentsAtKey(k, zero, zero);
            } else {
                prop.setSpatialAutoBezierAtKey(k, true);
                prop.setSpatialContinuousAtKey(k, true);
            }
        }
    }
    if (a.rove) {
        for (k = 2; k < last; k++) { prop.setRovingAtKey(k, true); }
    }
}

var CAVI_LIGHTS = {POINT: LightType.POINT, SPOT: LightType.SPOT, PARALLEL: LightType.PARALLEL,
    AMBIENT: LightType.AMBIENT, ENVIRONMENT: LightType.ENVIRONMENT};

// The project's footage item for the file at path, imported when there is none.
function caviFootage(path) {
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

// Sets the property ``match`` of ``group`` unless ``value`` is null.
function caviPut(group, match, value) {
    if (value !== null && value !== undefined) { group.property(match).setValue(value); }
}

// A Shape from {vertices, in_tangents, out_tangents, closed}.
function caviShape(spec) {
    var shape = new Shape();
    shape.vertices = spec.vertices;
    shape.inTangents = spec.in_tangents;
    shape.outTangents = spec.out_tangents;
    shape.closed = spec.closed;
    return shape;
}

// A solid of the comp's background color under its layers, so frames saved from the comp are not transparent.
function caviBackdrop(comp) {
    var backdrop = comp.layers.addSolid(comp.bgColor, "cavi-frame-bg", comp.width, comp.height, comp.pixelAspect,
        comp.duration);
    backdrop.moveToEnd();
    return backdrop;
}

// Removes a backdrop layer, and its solid when no other layer uses it.
function caviDropBackdrop(layer) {
    var source = layer.source;
    layer.remove();
    if (source.usedIn.length === 0) { source.remove(); }
}

// Sets the comp's renderer to one of those the comp offers.
function caviRenderer(comp, renderer) {
    var i, renderers = [];
    for (i = 0; i < comp.renderers.length; i++) { renderers.push(comp.renderers[i]); }
    if (("," + renderers.join(",") + ",").indexOf("," + renderer + ",") < 0) {
        caviFail("Renderer " + renderer + " is not one of " + renderers.join(", "));
    }
    comp.renderer = renderer;
}
