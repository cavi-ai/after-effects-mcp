$.evalFile(new File(CAVI_LIB));

function refuseFlat(layer) {
    if (layer instanceof CameraLayer) { caviFail("Layer " + layer.name + " is a camera"); }
    if (layer instanceof LightLayer) { caviFail("Layer " + layer.name + " is a light"); }
    if (layer.threeDLayer === true) { caviFail("Layer " + layer.name + " is 3D"); }
    if (layer.locked) { caviFail("Layer " + layer.name + " is locked"); }
}

// Corners of sourceRectAtTime in comp space, so scale, rotation and parents are part of the box.
function compBounds(layer, time) {
    var rect = layer.sourceRectAtTime(time, false), corners, i, point, box;
    corners = [[rect.left, rect.top], [rect.left + rect.width, rect.top],
        [rect.left, rect.top + rect.height], [rect.left + rect.width, rect.top + rect.height]];
    point = layer.toComp(corners[0], time);
    box = {left: point[0], top: point[1], right: point[0], bottom: point[1]};
    for (i = 1; i < corners.length; i++) {
        point = layer.toComp(corners[i], time);
        if (point[0] < box.left) { box.left = point[0]; }
        if (point[0] > box.right) { box.right = point[0]; }
        if (point[1] < box.top) { box.top = point[1]; }
        if (point[1] > box.bottom) { box.bottom = point[1]; }
    }
    return box;
}

function unionBounds(entries) {
    var box = {left: entries[0].before.left, top: entries[0].before.top, right: entries[0].before.right,
        bottom: entries[0].before.bottom}, i, item;
    for (i = 1; i < entries.length; i++) {
        item = entries[i].before;
        if (item.left < box.left) { box.left = item.left; }
        if (item.right > box.right) { box.right = item.right; }
        if (item.top < box.top) { box.top = item.top; }
        if (item.bottom > box.bottom) { box.bottom = item.bottom; }
    }
    return box;
}

function ancestry(layer) {
    var count = 0, guard = 0;
    while (layer.parent && guard < 100) {
        layer = layer.parent;
        count++;
        guard++;
    }
    return count;
}

// Parents first, so a child is placed from the bounds it has after its parent has moved.
function parentFirst(entries) {
    var order = [], i, j, tmp;
    for (i = 0; i < entries.length; i++) { order.push(i); }
    for (i = 1; i < order.length; i++) {
        tmp = order[i];
        j = i;
        while (j > 0 && ancestry(entries[order[j - 1]].layer) > ancestry(entries[tmp].layer)) {
            order[j] = order[j - 1];
            j--;
        }
        order[j] = tmp;
    }
    return order;
}

function orderByCenter(entries, axis) {
    var order = [], i, j, tmp;
    for (i = 0; i < entries.length; i++) { order.push(i); }
    for (i = 1; i < order.length; i++) {
        tmp = order[i];
        j = i;
        while (j > 0 && centerOf(entries[order[j - 1]].before, axis) > centerOf(entries[tmp].before, axis)) {
            order[j] = order[j - 1];
            j--;
        }
        order[j] = tmp;
    }
    return order;
}

function centerOf(box, axis) {
    return axis === "horizontal" ? (box.left + box.right) / 2 : (box.top + box.bottom) / 2;
}

function nearOf(box, axis) {
    return axis === "horizontal" ? box.left : box.top;
}

function farOf(box, axis) {
    return axis === "horizontal" ? box.right : box.bottom;
}

function sizeOf(box, axis) {
    return farOf(box, axis) - nearOf(box, axis);
}

function addPositionSpace(layer, dx, dy) {
    var pos = layer.property("ADBE Transform Group").property("ADBE Position"), i;
    function shifted(value) {
        var out = [value[0] + dx, value[1] + dy];
        if (value.length > 2) { out.push(value[2]); }
        return out;
    }
    if (pos.numKeys === 0) {
        pos.setValue(shifted(pos.value));
    } else {
        for (i = 1; i <= pos.numKeys; i++) { pos.setValueAtKey(i, shifted(pos.keyValue(i))); }
    }
    return [dx, dy];
}

// dx, dy are comp space. Position is parent space when the layer has a parent.
function moveBy(layer, dx, dy, time) {
    var space;
    if (dx === 0 && dy === 0) { return [0, 0]; }
    space = layer.parent ? layer.parent.fromCompVec([dx, dy], time) : [dx, dy];
    return addPositionSpace(layer, space[0], space[1]);
}

function shiftFor(current, edge, ref) {
    var dx = 0, dy = 0, rcx, rcy, ccx, ccy;
    if (edge === "left") { dx = ref.left - current.left; }
    else if (edge === "right") { dx = ref.right - current.right; }
    else if (edge === "top") { dy = ref.top - current.top; }
    else if (edge === "bottom") { dy = ref.bottom - current.bottom; }
    else if (edge === "hcenter" || edge === "center") {
        rcx = (ref.left + ref.right) / 2;
        ccx = (current.left + current.right) / 2;
        dx = rcx - ccx;
    }
    if (edge === "vcenter" || edge === "center") {
        rcy = (ref.top + ref.bottom) / 2;
        ccy = (current.top + current.bottom) / 2;
        dy = rcy - ccy;
    }
    if (edge !== "left" && edge !== "right" && edge !== "top" && edge !== "bottom" && edge !== "hcenter" &&
            edge !== "vcenter" && edge !== "center") {
        caviFail("Unknown edge " + edge);
    }
    return [dx, dy];
}

// Absolute near edge of each box. The first stays put; with no gap the last stays put too.
function distributeTargets(entries, axis, gap) {
    var order = orderByCenter(entries, axis), targets = [], n = order.length, i, middle = 0, gaps, spacing, cursor, idx;
    for (i = 0; i < entries.length; i++) { targets.push(nearOf(entries[i].before, axis)); }
    if (n < 2) { return targets; }
    if (gap === null) {
        for (i = 1; i < n - 1; i++) { middle += sizeOf(entries[order[i]].before, axis); }
        gaps = n - 1;
        spacing = (nearOf(entries[order[n - 1]].before, axis) - farOf(entries[order[0]].before, axis) - middle) / gaps;
        cursor = farOf(entries[order[0]].before, axis);
        for (i = 1; i < n - 1; i++) {
            idx = order[i];
            targets[idx] = cursor + spacing;
            cursor = targets[idx] + sizeOf(entries[idx].before, axis);
        }
    } else {
        cursor = farOf(entries[order[0]].before, axis);
        for (i = 1; i < n; i++) {
            idx = order[i];
            targets[idx] = cursor + gap;
            cursor = targets[idx] + sizeOf(entries[idx].before, axis);
        }
    }
    return targets;
}

function writeAnchor(anchor, cx, cy) {
    var i;
    function point(value) {
        if (value.length > 2) { return [cx, cy, value[2]]; }
        return [cx, cy];
    }
    if (anchor.numKeys === 0) {
        anchor.setValue(point(anchor.value));
        return;
    }
    for (i = 1; i <= anchor.numKeys; i++) { anchor.setValueAtKey(i, point(anchor.keyValue(i))); }
}

// Anchor moves to the source-rect center. Position takes the same visual delta so the layer stays put.
function centerAnchor(layer, time) {
    var anchor = layer.property("ADBE Transform Group").property("ADBE Anchor Point");
    var rect = layer.sourceRectAtTime(time, false), value = anchor.valueAtTime(time, false);
    var compDelta = layer.toCompVec([rect.left + rect.width / 2 - value[0], rect.top + rect.height / 2 - value[1]], time);
    var posDelta = layer.parent ? layer.parent.fromCompVec(compDelta, time) : compDelta;
    writeAnchor(anchor, rect.left + rect.width / 2, rect.top + rect.height / 2);
    return addPositionSpace(layer, posDelta[0], posDelta[1]);
}

function applyTargets(entries, targets, axis, time) {
    var order = parentFirst(entries), i, entry, current, delta;
    for (i = 0; i < order.length; i++) {
        entry = entries[order[i]];
        current = compBounds(entry.layer, time);
        if (axis === "horizontal") {
            delta = [targets[order[i]] - current.left, 0];
        } else {
            delta = [0, targets[order[i]] - current.top];
        }
        entry.moved = moveBy(entry.layer, delta[0], delta[1], time);
    }
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), entries = [], i, layer, ref, order, entry, current, shift, targets, moved;
    for (i = 0; i < a.layers.length; i++) {
        layer = caviLayer(comp, a.layers[i]);
        refuseFlat(layer);
        entries.push({layer: layer, before: compBounds(layer, a.time), moved: [0, 0]});
    }
    if (a.action === "align") {
        ref = a.to === "selection" ? unionBounds(entries) : {left: 0, top: 0, right: comp.width, bottom: comp.height};
        order = parentFirst(entries);
        for (i = 0; i < order.length; i++) {
            entry = entries[order[i]];
            current = compBounds(entry.layer, a.time);
            shift = shiftFor(current, a.edge, ref);
            entry.moved = moveBy(entry.layer, shift[0], shift[1], a.time);
        }
    } else if (a.action === "distribute") {
        targets = distributeTargets(entries, a.axis, a.gap);
        applyTargets(entries, targets, a.axis, a.time);
    } else if (a.action === "anchor") {
        for (i = 0; i < entries.length; i++) {
            entries[i].moved = centerAnchor(entries[i].layer, a.time);
        }
    } else {
        caviFail("Unknown action " + a.action);
    }
    moved = [];
    for (i = 0; i < entries.length; i++) {
        moved.push({layer: entries[i].layer.name, index: entries[i].layer.index, before: entries[i].before,
            after: compBounds(entries[i].layer, a.time), moved: entries[i].moved});
    }
    caviReport({comp: comp.name, action: a.action, layers: moved, errors: []});
})();
