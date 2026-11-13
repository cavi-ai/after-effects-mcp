// Helpers shared by the tool templates. ExtendScript is ES3: no JSON, no Array.indexOf.
var CAVI_TRANSFORM = {
    position: "ADBE Position", anchor: "ADBE Anchor Point", scale: "ADBE Scale", rotation: "ADBE Rotate Z",
    rotationx: "ADBE Rotate X", rotationy: "ADBE Rotate Y", orientation: "ADBE Orientation", opacity: "ADBE Opacity"
};

function caviFail(message) {
    throw new Error(message);
}

function caviComp(name) {
    var i, item;
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof CompItem && item.name === name) {
            return item;
        }
    }
    return caviFail("No comp named " + name);
}

function caviLayer(comp, ref) {
    var i;
    if (typeof ref === "number") {
        if (ref < 1 || ref > comp.numLayers) {
            caviFail("Comp " + comp.name + " has no layer " + ref);
        }
        return comp.layer(ref);
    }
    for (i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === ref) {
            return comp.layer(i);
        }
    }
    return caviFail("Comp " + comp.name + " has no layer named " + ref);
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

// Keys as [{time, value, ease_in, ease_out, interpolation}]; the first listed time wins on a repeat.
function caviKeys(prop, keys, fallback) {
    var i, k, key, inEase, outEase, kind, kinds = {LINEAR: KeyframeInterpolationType.LINEAR,
        BEZIER: KeyframeInterpolationType.BEZIER, HOLD: KeyframeInterpolationType.HOLD};
    for (i = 0; i < keys.length; i++) {
        prop.setValueAtTime(keys[i].time, keys[i].value);
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
    return {index: index, comp: item.comp.name, status: caviStatus(item), render: item.render,
        label: item.comp.label, file: module.file ? module.file.fsName : null,
        output_module: module.name, templates: templates};
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
    if (has("font")) { doc.font = s.font; }
    if (has("size")) { doc.fontSize = s.size; }
    if (has("fill")) { doc.applyFill = true; doc.fillColor = s.fill; }
    if (has("stroke")) { doc.applyStroke = true; doc.strokeColor = s.stroke; }
    if (has("stroke_width")) { doc.strokeWidth = s.stroke_width; }
    if (has("tracking")) { doc.tracking = s.tracking; }
    if (has("leading")) { doc.autoLeading = false; doc.leading = s.leading; }
    if (has("justification")) { doc.justification = caviEnum(CAVI_JUSTIFY, s.justification, "justification"); }
    if (has("box")) { doc.boxTextSize = s.box; }
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
    prop.setValue(value);
}

// The project folder named name, created at the root when absent.
function caviFolder(name) {
    var i, item;
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof FolderItem && item.name === name) {
            return item;
        }
    }
    return app.project.items.addFolder(name);
}
