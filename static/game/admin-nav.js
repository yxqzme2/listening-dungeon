/* The Listening Dungeon — top bar for the admin pages. Replaces the old
 * <nav class="admin-nav"> with the paper nav and marks the current page. */
(function () {
  const LINKS = [["/admin", "Admin home"], ["/admin/monsters", "Monsters"], ["/admin/loot", "Armory"], ["/admin/radar", "Radar"],
    ["/admin/requests", "Requests"], ["/admin/ops", "System Core"], ["/", "The game"], ["/admin/logout", "Log out"]];
  const here = location.pathname.replace(/\/$/, "") || "/admin";
  const same = (href) => href === here || (href === "/admin/loot" && here === "/admin/armory");
  const header = document.createElement("header");
  header.className = "paper-top";
  header.innerHTML = `<a class="brand" href="/admin">Dungeon Admin<small>Behind the curtain.</small></a>
    <nav aria-label="Admin">${LINKS.map(([href, name]) => `<a href="${href}"${same(href) ? ' aria-current="page"' : ""}>${name}</a>`).join("")}</nav>`;
  const old = document.querySelector("nav.admin-nav");
  if (old) old.replaceWith(header); else document.body.prepend(header);
  document.body.classList.add("paper");
})();
