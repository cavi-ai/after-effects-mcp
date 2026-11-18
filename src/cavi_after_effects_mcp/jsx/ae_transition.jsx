$.evalFile(new File(CAVI_LIB));

function completion(effect) {
    var prop = effect.property("Transition Completion") || effect.property("Completion");
    if (!prop) { caviFail("Effect " + effect.name + " has no completion parameter"); }
    return prop;
}

function fade(layer, keys, ease) {
    caviKeys(caviProp(layer, "opacity"), keys, ease);
}

function key(time, value) {
    return {time: time, value: value, ease_in: null, ease_out: null, interpolation: null};
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), d = a.seconds !== null ? a.seconds : a.frames / comp.frameRate;
    var from = a.from_layer !== null ? caviLayer(comp, a.from_layer) : null;
    var to = a.to_layer !== null ? caviLayer(comp, a.to_layer) : null;
    var single = a.layer !== null ? caviLayer(comp, a.layer) : null;
    var target, edge = a.edge, start, end, mid, needed, effect, dip, applied = [], prop, top, trimmed = null;
    if (d <= 0) { caviFail("Duration must be positive"); }
    if (single) {
        target = single;
        end = edge === "in" ? single.inPoint + d : single.outPoint;
        start = end - d;
    } else {
        start = to.inPoint;
        end = start + d;
        mid = start + d / 2;
        // Only the upper layer changes, over the lower one: the outgoing layer goes out or the incoming one comes in.
        edge = from.index < to.index ? "out" : "in";
        target = edge === "out" ? from : to;
        needed = a.kind === "dip" ? mid : end;
        if (from.outPoint < needed - comp.frameDuration / 2) {
            caviFail("from_layer " + from.name + " ends at " + from.outPoint + " s, before " + needed +
                " s; overlap the layers by the transition length");
        }
    }
    if (a.kind === "crossfade") {
        fade(target, edge === "in" ? [key(start, 0), key(end, 100)] : [key(start, 100), key(end, 0)], a.ease);
        applied.push("opacity");
    } else if (a.kind === "dip") {
        dip = comp.layers.addSolid(a.color, "dip", comp.width, comp.height, 1, comp.duration);
        dip.moveToBeginning();
        dip.inPoint = start; dip.outPoint = end;
        if (single) {
            fade(dip, edge === "in" ? [key(start, 100), key(end, 0)] : [key(start, 0), key(end, 100)], a.ease);
        } else {
            // The outgoing layer shows until the dip is full and the incoming one after it.
            from.outPoint = mid;
            to.inPoint = mid;
            trimmed = {from_out_point: from.outPoint, to_in_point: to.inPoint};
            fade(dip, [key(start, 0), key(mid, 100), key(end, 0)], a.ease);
        }
        applied.push("dip");
    } else {
        caviGuard3D(comp, target, "an effect");
        effect = target.property("ADBE Effect Parade").addProperty(a.match_name);
        if (!effect) { caviFail("This install has no effect " + a.match_name); }
        effect.name = a.kind;
        prop = completion(effect);
        // Completion runs 0 to 100 on the stock effects and 0 to 1 on some CC ones.
        top = prop.maxValue > 0 && prop.maxValue < 100 ? prop.maxValue : 100;
        caviKeys(prop, edge === "in" ? [key(start, top), key(end, 0)] : [key(start, 0), key(end, top)], a.ease);
        applied.push(effect.matchName);
    }
    caviReport({comp: comp.name, kind: a.kind, start: start, end: end, seconds: d, applied: applied,
        layer: target.name, edge: edge, trimmed: trimmed, errors: []});
})();
