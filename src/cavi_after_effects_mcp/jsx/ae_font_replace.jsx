$.evalFile(new File(CAVI_LIB));

// Replaces every use of a font in the project's text with an installed font, through Project.replaceFont.
(function () {
    var a = CAVI_ARGS, used, targets, to = null, i, j, layer, layers = [], seen = {}, replaced = false, found = false;
    if (typeof app.project.replaceFont !== "function") {
        caviFail("Replacing fonts needs After Effects 24.5 or later");
    }
    targets = app.fonts.getFontsByPostScriptName(a.to);
    for (i = 0; i < targets.length && to === null; i++) {
        if (!targets[i].isSubstitute) { to = targets[i]; }
    }
    if (to === null) {
        caviFail("Font " + a.to + " is not installed; ae_fonts lists the PostScript names");
    }
    used = app.project.usedFonts;
    for (i = 0; i < used.length; i++) {
        if (used[i].font.postScriptName !== a.font) { continue; }
        found = true;
        for (j = 0; j < used[i].usedAt.length; j++) {
            if (seen[used[i].usedAt[j].layerID]) { continue; }
            seen[used[i].usedAt[j].layerID] = true;
            layer = app.project.layerByID(used[i].usedAt[j].layerID);
            layers.push({comp: layer.containingComp.name, layer: layer.name, index: layer.index});
        }
        replaced = app.project.replaceFont(used[i].font, to, !a.fallback) || replaced;
    }
    if (!found) {
        caviFail("No text uses font " + a.font + "; ae_fonts with used lists the fonts in use");
    }
    caviReport({font: a.font, to: to.postScriptName, replaced: replaced, layers: layers, errors: []});
})();
