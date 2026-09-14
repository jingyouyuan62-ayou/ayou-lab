const grid = document.getElementById("archive-grid");
const status = document.getElementById("archive-status");

fetch("data/entries.json")
    .then((response) => {
        if (!response.ok) {
            throw new Error("Failed to load entries.json");
        }
        return response.json();
    })
    .then((entries) => {
        status.remove();

        if (entries.length === 0) {
            grid.textContent = "The archive is still growing.";
            return;
        }

        entries.forEach((entry) => {
            grid.appendChild(createCard(entry));
        });
    })
    .catch((error) => {
        status.textContent = "Could not load the archive. " + error.message;
    });

function createCard(entry) {
    const card = document.createElement("article");
    card.className = "entry-card";

    const image = document.createElement("img");
    image.src = entry.image;
    image.alt = entry.title;
    image.loading = "lazy";

    const body = document.createElement("div");
    body.className = "entry-card-body";

    const title = document.createElement("h2");
    title.textContent = entry.title;

    const meta = document.createElement("p");
    meta.className = "entry-meta";
    meta.textContent = `${entry.date} · ${entry.medium} · ${entry.source}`;

    const note = document.createElement("p");
    note.className = "entry-note";
    note.textContent = entry.note;

    const tags = document.createElement("p");
    tags.className = "entry-tags";
    tags.textContent = entry.tags.join(" / ");

    body.append(title, meta, note, tags);
    card.append(image, body);

    return card;
}
