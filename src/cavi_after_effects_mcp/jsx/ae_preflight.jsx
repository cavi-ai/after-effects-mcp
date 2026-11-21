$.evalFile(new File(CAVI_LIB));

// Missing footage, substitute fonts and broken expressions, plus odd frame sizes. Reads only.
function layerSource(layer) {
    try {
        return layer.source;
    } catch (noSource) {
        return null;
    }
}

function footagePath(item) {
    try {
        return item.mainSource && item.mainSource.file ? item.mainSource.file.fsName : null;
    } catch (none) {
        return null;
    }
}

// The comp and every precomp reached through a layer source, each once.
function compsFrom(root) {
    var list = [root], seen = {}, i, j, layer, source;
    seen[root.id] = true;
    for (i = 0; i < list.length; i++) {
        for (j = 1; j <= list[i].numLayers; j++) {
            layer = list[i].layer(j);
            source = layerSource(layer);
            if (source instanceof CompItem && !seen[source.id]) {
                seen[source.id] = true;
                list.push(source);
            }
        }
    }
    return list;
}

function visitExpressions(prop, path, layer, compName, out) {
    var i, expression, error, child;
    if (prop.propertyType === PropertyType.PROPERTY) {
        try {
            if (!prop.canSetExpression) { return; }
            expression = prop.expression;
            if (expression === "") { return; }
            error = prop.expressionError;
            if (error !== "") {
                out.push({comp: compName, layer: layer.name, property: path, error: error});
            }
        } catch (skipped) { return; }
        return;
    }
    for (i = 1; i <= prop.numProperties; i++) {
        try {
            child = prop.property(i);
            visitExpressions(child, path + "/" + child.name, layer, compName, out);
        } catch (hidden) { continue; }
    }
}

function scanExpressions(comp, out) {
    var i, layer;
    for (i = 1; i <= comp.numLayers; i++) {
        layer = comp.layer(i);
        visitExpressions(layer, layer.name, layer, comp.name, out);
    }
}

function recordFootage(item, out, seen) {
    if (!(item instanceof FootageItem) || item.footageMissing !== true || seen[item.id]) { return; }
    seen[item.id] = true;
    out.push({id: item.id, name: item.name, file: footagePath(item)});
}

function footageIn(comps, out) {
    var seen = {}, i, j, source;
    for (i = 0; i < comps.length; i++) {
        for (j = 1; j <= comps[i].numLayers; j++) {
            source = layerSource(comps[i].layer(j));
            if (source instanceof FootageItem) { recordFootage(source, out, seen); }
        }
    }
}

function projectFootage(out) {
    var seen = {}, i;
    for (i = 1; i <= app.project.numItems; i++) {
        recordFootage(app.project.item(i), out, seen);
    }
}

function substituteFonts(compIds) {
    var used, i, j, font, layers, seen, layer, id, keep, found = [];
    if (app.project.usedFonts === undefined) {
        caviFail("Listing the fonts in use needs After Effects 24.5 or later");
    }
    used = app.project.usedFonts;
    for (i = 0; i < used.length; i++) {
        font = used[i].font;
        if (!font.isSubstitute) { continue; }
        layers = [];
        seen = {};
        keep = compIds === null;
        for (j = 0; j < used[i].usedAt.length; j++) {
            id = used[i].usedAt[j].layerID;
            if (seen[id]) { continue; }
            seen[id] = true;
            layer = app.project.layerByID(id);
            if (!layer || !layer.containingComp) { continue; }
            if (compIds !== null && !compIds[layer.containingComp.id]) { continue; }
            layers.push({comp: layer.containingComp.name, layer: layer.name, index: layer.index});
            keep = true;
        }
        if (keep) { found.push({postscript: font.postScriptName, layers: layers}); }
    }
    return found;
}

function oddFrame(comp, warnings) {
    if (comp.width % 2 !== 0 || comp.height % 2 !== 0) {
        warnings.push({comp: comp.name, width: comp.width, height: comp.height, warning: "odd frame size"});
    }
}

(function () {
    var a = CAVI_ARGS, root, reached, compIds = null, i, item, comps = [],
        missingFootage = [], missingFonts, broken = [], warnings = [];
    if (a.comp !== null) {
        root = caviComp(a.comp);
        reached = compsFrom(root);
        compIds = {};
        for (i = 0; i < reached.length; i++) { compIds[reached[i].id] = true; }
        footageIn(reached, missingFootage);
        for (i = 0; i < reached.length; i++) { scanExpressions(reached[i], broken); }
        oddFrame(root, warnings);
    } else {
        projectFootage(missingFootage);
        for (i = 1; i <= app.project.numItems; i++) {
            item = app.project.item(i);
            if (item instanceof CompItem) { comps.push(item); }
        }
        for (i = 0; i < comps.length; i++) {
            scanExpressions(comps[i], broken);
            oddFrame(comps[i], warnings);
        }
    }
    missingFonts = substituteFonts(compIds);
    caviReport({
        verdict: (missingFootage.length || missingFonts.length || broken.length) ? "fail" : "pass",
        missing_footage: missingFootage,
        missing_fonts: missingFonts,
        broken_expressions: broken,
        warnings: warnings,
        errors: []
    });
})();
