# Back to top

All public pages include `includes/back_to_top.html` through `base.html`.
The standalone server-error page includes it directly, without depending on
Wagtail's database-backed navigation or site lookup.

The control is a native link styled as a button at the lower right. It shows an
up arrow and the visible label “Back to top”. Its target is the skip link at the
start of the page, so activation returns keyboard navigation to the beginning.
On the standalone server-error page, the target is the error heading.

With JavaScript, the control appears when the header leaves the viewport. It
remains visible if it has keyboard focus, and hides after focus leaves when the
header is visible again. Without JavaScript or IntersectionObserver, the native
link remains available. Fragment navigation is immediate and adds no animation.

The button uses the existing primary-button colour family and visible focus
outline. Its arrow is decorative. Footer clearance and scroll padding leave
room for the control; JavaScript also scrolls a focused element's label clear if
it would overlap the control. For large card links, this keeps the heading in
view. The editor toolbar sits at the opposite corner.
On narrow screens the main menu scrolls with the page, preserving reading space
above the floating control, including when text is enlarged.

Implementation: `aakh/templates/base.html`, `aakh/templates/500.html`,
`aakh/templates/includes/back_to_top.html`, `aakh/static/css/aakh.css`,
`aakh/static/css/tokens.css`, and `aakh/static/js/aakh.js`.
