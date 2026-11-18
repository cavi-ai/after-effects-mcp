$.evalFile(new File(CAVI_LIB));

var FLOOR = -100, STEPS = 8;

function clearKeys(prop) {
    var i;
    for (i = prop.numKeys; i >= 1; i--) { prop.removeKey(i); }
}

// Levels at gain g (0 to 1) of base, per channel; g = 0 is the floor.
function gain(base, g) {
    var out = [], c;
    for (c = 0; c < base.length; c++) {
        out.push(g > 0 ? Math.max(FLOOR, base[c] + 20 * Math.log(g) / Math.LN10) : FLOOR);
    }
    return out;
}

// STEPS + 1 keys whose gain rises (or falls) linearly in amplitude over the fade.
function fade(levels, start, length, base, rising) {
    var k, g;
    for (k = 0; k <= STEPS; k++) {
        g = k / STEPS;
        levels.setValueAtTime(start + length * g, gain(base, rising ? g : 1 - g));
    }
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), levels, i, baseIn, baseOut, keys = [];
    if (!layer.hasAudio) { caviFail("Layer " + layer.name + " has no audio"); }
    if ((a.fade_in || 0) + (a.fade_out || 0) > layer.outPoint - layer.inPoint + 1e-6) {
        caviFail("fade_in and fade_out add up to " + ((a.fade_in || 0) + (a.fade_out || 0)) + " s; layer " + layer.name
            + " lasts " + (layer.outPoint - layer.inPoint) + " s");
    }
    levels = layer.property("ADBE Audio Group").property("ADBE Audio Levels");
    if (a.enabled !== null) { layer.audioEnabled = a.enabled; }
    if (a.level_keys.length) {
        clearKeys(levels);
        caviKeys(levels, a.level_keys, null);
    } else if (a.level !== null) {
        clearKeys(levels);
        levels.setValue(a.level);
    }
    if (a.fade_in !== null) { baseIn = levels.valueAtTime(layer.inPoint + a.fade_in, false); }
    if (a.fade_out !== null) { baseOut = levels.valueAtTime(layer.outPoint - a.fade_out, false); }
    if (a.fade_in !== null) { fade(levels, layer.inPoint, a.fade_in, baseIn, true); }
    if (a.fade_out !== null) { fade(levels, layer.outPoint - a.fade_out, a.fade_out, baseOut, false); }
    for (i = 1; i <= levels.numKeys; i++) { keys.push({time: levels.keyTime(i), value: levels.keyValue(i)}); }
    caviReport({comp: comp.name, layer: layer.name, audio_enabled: layer.audioEnabled, levels: levels.value, keys: keys,
        errors: []});
})();
