$.evalFile(new File(CAVI_LIB));

var FLOOR = -100;

function clearKeys(prop) {
    var i;
    for (i = prop.numKeys; i >= 1; i--) { prop.removeKey(i); }
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), levels, i, baseIn, baseOut, keys = [];
    if (!layer.hasAudio) { caviFail("Layer " + layer.name + " has no audio"); }
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
    if (a.fade_in !== null) {
        levels.setValueAtTime(layer.inPoint, [FLOOR, FLOOR]);
        levels.setValueAtTime(layer.inPoint + a.fade_in, baseIn);
    }
    if (a.fade_out !== null) {
        levels.setValueAtTime(layer.outPoint - a.fade_out, baseOut);
        levels.setValueAtTime(layer.outPoint, [FLOOR, FLOOR]);
    }
    for (i = 1; i <= levels.numKeys; i++) { keys.push({time: levels.keyTime(i), value: levels.keyValue(i)}); }
    caviReport({comp: comp.name, layer: layer.name, audio_enabled: layer.audioEnabled, levels: levels.value, keys: keys,
        errors: []});
})();
