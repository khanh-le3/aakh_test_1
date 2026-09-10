/* Persist Wagtail's own metric; do not duplicate its text extraction or formula.
 * https://docs.wagtail.org/en/7.4/extending/editor_api.html#the-preview-panel
 */
(function () {
    "use strict";

    var pending = false;
    var resuming = false;
    var contentVersion = 0;

    // Use Wagtail's change notifications, including StreamField add/reorder,
    // plus immediate input events. Draftail normalizes hidden JSON after load,
    // so comparing raw form strings would mistake that for a content edit.
    document.addEventListener("w-unsaved:add", function () { contentVersion += 1; });
    ["input", "change"].forEach(function (name) {
        document.addEventListener(name, function (event) {
            if (event.target.closest("form[data-edit-form]")) contentVersion += 1;
        });
    });

    async function extractMetric(preview) {
        // Finish any earlier update before asking Wagtail to preview this save.
        await preview.updatePromise;
        await preview.reloadPromise;
        await preview.contentChecksPromise;
        var before = contentVersion;
        var valid = await preview.setPreviewData();
        await preview.reloadPromise;
        await preview.contentChecksPromise;
        if (!valid || before !== contentVersion) return null;

        var content = await preview.extractContent();
        if (!content || before !== contentVersion) return null;
        var minutes = preview.extractMetrics(content).readingTime;
        return Number.isInteger(minutes) && minutes >= 0 ? minutes : null;
    }

    // Capture before Wagtail's submit handlers so its normal save, publish and
    // moderation actions still receive the original submit button exactly once.
    document.addEventListener("submit", async function (event) {
        var form = event.target;
        if (!form.matches("form[data-edit-form]")) return;
        var field = form.elements.namedItem("reading_time");
        if (!field || resuming) return;
        field.value = "";
        var preview = window.wagtail?.app?.queryController("w-preview");
        if (!preview?.extractMetrics) return;

        event.preventDefault();
        event.stopImmediatePropagation();
        if (pending) return;
        pending = true;
        var submitter = event.submitter;
        var busy = form.getAttribute("aria-busy");
        form.setAttribute("aria-busy", "true");
        var timer;
        try {
            // Finish the original submit event before any immediate failure
            // can resume it; browsers otherwise suppress nested requestSubmit.
            await new Promise(function (resolve) { window.setTimeout(resolve, 0); });
            // Preview errors must not prevent editors from saving their work.
            // With no current metric we omit read time on the public page.
            var minutes = await Promise.race([
                extractMetric(preview),
                new Promise(function (resolve) {
                    timer = window.setTimeout(function () { resolve(null); }, 10000);
                }),
            ]);
            field.value = minutes === null ? "" : String(minutes);
        } catch (error) {
            field.value = "";
        } finally {
            window.clearTimeout(timer);
            if (busy === null) form.removeAttribute("aria-busy");
            else form.setAttribute("aria-busy", busy);
            pending = false;
            resuming = true;
            try {
                // Wagtail's progress button disables itself while we wait.
                // A disabled submitter loses its name/value (e.g. Publish).
                if (submitter) submitter.disabled = false;
                form.requestSubmit(submitter);
            } finally {
                resuming = false;
            }
        }
    }, true);
})();
