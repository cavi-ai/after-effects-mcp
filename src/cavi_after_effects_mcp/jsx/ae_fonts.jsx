$.evalFile(new File(CAVI_LIB));

// Installed fonts, or with ``used`` the fonts the project's text uses, each with the layers that use it.
(function () {
    var a = CAVI_ARGS, found = [], i, j, font, needle = a.filter.toLowerCase(), all, used, layers, seen, layer;
    function matches(f) {
        return (f.postScriptName + " " + f.familyName + " " + f.styleName).toLowerCase().indexOf(needle) >= 0;
    }
    if (a.used) {
        if (app.project.usedFonts === undefined) {
            caviFail("Listing the fonts in use needs After Effects 24.5 or later");
        }
        used = app.project.usedFonts;
        for (i = 0; i < used.length; i++) {
            font = used[i].font;
            if (!matches(font)) { continue; }
            layers = [];
            seen = {};
            for (j = 0; j < used[i].usedAt.length; j++) {
                if (seen[used[i].usedAt[j].layerID]) { continue; }
                seen[used[i].usedAt[j].layerID] = true;
                layer = app.project.layerByID(used[i].usedAt[j].layerID);
                layers.push({comp: layer.containingComp.name, layer: layer.name, index: layer.index});
            }
            found.push({postscript: font.postScriptName, family: font.familyName, style: font.styleName,
                missing: font.isSubstitute, layers: layers});
        }
    } else {
        all = app.fonts.allFonts;
        for (i = 0; i < all.length; i++) {
            for (j = 0; j < all[i].length; j++) {
                font = all[i][j];
                if (matches(font)) {
                    found.push({postscript: font.postScriptName, family: font.familyName, style: font.styleName});
                }
            }
        }
    }
    caviReport({fonts: found.slice(0, a.limit), count: found.length, errors: []});
})();
