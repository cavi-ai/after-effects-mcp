$.evalFile(new File(CAVI_LIB));

function describe(property) {
    var list = [], i, value;
    for (i = 1; i <= property.numKeys; i++) {
        value = property.keyValue(i);
        list.push({time: property.keyTime(i), comment: value.comment, duration: value.duration,
            chapter: value.chapter});
    }
    return list;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), target, i, marker, value;
    target = a.layer === null ? comp.markerProperty : caviLayer(comp, a.layer).property("ADBE Marker");
    if (a.clear) {
        for (i = target.numKeys; i >= 1; i--) { target.removeKey(i); }
    }
    for (i = 0; i < a.markers.length; i++) {
        marker = a.markers[i];
        value = new MarkerValue(marker.comment);
        value.duration = marker.duration;
        if (marker.chapter !== null) { value.chapter = marker.chapter; }
        target.setValueAtTime(marker.time, value);
    }
    caviReport({comp: comp.name, layer: a.layer === null ? null : caviLayer(comp, a.layer).name,
        count: target.numKeys, markers: describe(target), errors: []});
})();
