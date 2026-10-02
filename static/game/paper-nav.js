/* The Listening Dungeon — top bar for the library pages. Replaces the old
 * <nav class="nav-bar"> with the hub's paper nav and marks the current page. */
(function () {
  const LINKS = [["/", "Hub"], ["/#party", "Party"], ["/chronicle", "Chronicle"], ["/archives", "Stats"], ["/tier", "Tier List"],
    ["/recommendations", "Recommendations"], ["/radar", "Radar"], ["/request", "Request"], ["/static/game/bestiary.html", "Bestiary"]];
  const here = location.pathname.replace(/\/$/, "") || "/";
  const header = document.createElement("header");
  header.className = "paper-top";
  header.innerHTML = `<a class="brand" href="/">The Listening Dungeon<small>Every book you finish is a dungeon.</small></a>
    <nav aria-label="Main">${LINKS.map(([href, name]) => `<a href="${href}"${href === here ? ' aria-current="page"' : ""}>${name}</a>`).join("")}</nav>`;
  const old = document.querySelector("nav.nav-bar");
  if (old) old.replaceWith(header); else document.body.prepend(header);
  document.body.classList.add("paper");
})();
