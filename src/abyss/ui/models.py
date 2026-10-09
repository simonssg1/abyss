"""Modèles Qt des presets pour le QML : liste + proxy de filtrage (catégorie, recherche)."""

from __future__ import annotations

import unicodedata

from PySide6.QtCore import (QAbstractListModel, QByteArray, QModelIndex, QPersistentModelIndex, QSortFilterProxyModel,
                            Qt, Property, Signal, Slot)

from abyss.hotkeys import pretty
from abyss.presets import Preset

ALL = "Toutes"

# Entrée non cliquable « Voix IA » (catégorie IA, badge Bientôt) : la conversion RVC arrive en v2.
AI_PLACEHOLDER = Preset("Voix IA", None, [], description="Conversion de voix par IA",
                        categories=["IA"], icon="sparkles", badge="soon", id="ai-voice")

ROLES = ("id", "name", "description", "category", "categories", "icon", "badge", "hotkey", "intensity",
         "toneLow", "toneHigh", "effects", "isUser", "enabled")


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


class PresetModel(QAbstractListModel):
    countChanged = Signal()

    def __init__(self, presets: list[Preset] | None = None, hotkeys: dict[str, str] | None = None,
                 parent=None, with_placeholder: bool = True):
        super().__init__(parent)
        self._hotkeys = hotkeys or {}
        self._with_placeholder = with_placeholder
        self._items: list[Preset] = []
        self._roles = {Qt.ItemDataRole.UserRole + i + 1: name for i, name in enumerate(ROLES)}
        self.set_presets(presets or [])

    # ----- API Python -----
    def set_presets(self, presets: list[Preset]) -> None:
        self.beginResetModel()
        self._items = list(presets) + ([AI_PLACEHOLDER] if self._with_placeholder else [])
        self.endResetModel()
        self.countChanged.emit()

    def set_hotkeys(self, hotkeys: dict[str, str]) -> None:
        self._hotkeys = hotkeys
        if self._items:
            self.dataChanged.emit(self.index(0), self.index(len(self._items) - 1))

    def presets(self) -> list[Preset]:
        return [p for p in self._items if p is not AI_PLACEHOLDER]

    def find(self, preset_id: str) -> Preset | None:
        return next((p for p in self._items if p.id == preset_id and p is not AI_PLACEHOLDER), None)

    def row_of(self, preset_id: str) -> int:
        return next((i for i, p in enumerate(self._items) if p.id == preset_id), -1)

    def refresh(self, preset_id: str) -> None:
        row = self.row_of(preset_id)
        if row >= 0:
            self.dataChanged.emit(self.index(row), self.index(row))

    # ----- QAbstractListModel -----
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def roleNames(self) -> dict:
        return {k: QByteArray(v.encode()) for k, v in self._roles.items()}

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        p = self._items[index.row()]
        name = self._roles.get(role) or ("name" if role == Qt.ItemDataRole.DisplayRole else None)
        return self.value(p, name) if name else None

    def value(self, p: Preset, name: str):
        if name == "id":
            return p.id
        if name == "name":
            return p.name
        if name == "description":
            return p.description
        if name == "category":
            return p.categories[0] if p.categories else ""
        if name == "categories":
            return list(p.categories)
        if name == "icon":
            return p.icon or "mic"
        if name == "badge":
            return p.badge
        if name == "hotkey":
            combo = self._hotkeys.get(f"preset_{p.hotkey_index}") if p.hotkey_index else None
            return pretty(combo) if combo else ""
        if name == "intensity":
            return p.intensity
        if name == "toneLow":
            return p.tone_low_hz
        if name == "toneHigh":
            return p.tone_high_hz
        if name == "effects":
            return [dict(e) for e in p.effects]
        if name == "isUser":
            return p.is_user
        if name == "enabled":
            return p is not AI_PLACEHOLDER
        return None

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    @Slot(str, result="QVariantMap")
    def get(self, preset_id: str) -> dict:
        p = self.find(preset_id) or (AI_PLACEHOLDER if preset_id == AI_PLACEHOLDER.id else None)
        return {name: self.value(p, name) for name in ROLES} if p else {}


class PresetFilterModel(QSortFilterProxyModel):
    """Filtre par catégorie (« Toutes » = aucune restriction) et par texte (nom, description)."""

    categoryChanged = Signal()
    searchChanged = Signal()

    def __init__(self, source: PresetModel, parent=None):
        super().__init__(parent)
        self._category = ALL
        self._search = ""
        self.setSourceModel(source)
        self.setDynamicSortFilter(True)

    def _get_category(self) -> str:
        return self._category

    def _set_category(self, value: str) -> None:
        value = value or ALL
        if value != self._category:
            self.beginFilterChange()
            self._category = value
            self.endFilterChange()
            self.categoryChanged.emit()

    def _get_search(self) -> str:
        return self._search

    def _set_search(self, value: str) -> None:
        if value != self._search:
            self.beginFilterChange()
            self._search = value
            self.endFilterChange()
            self.searchChanged.emit()

    category = Property(str, _get_category, _set_category, notify=categoryChanged)
    search = Property(str, _get_search, _set_search, notify=searchChanged)

    def filterAcceptsRow(self, row: int, parent) -> bool:
        model: PresetModel = self.sourceModel()
        p = model._items[row]
        if self._category != ALL and self._category not in p.categories:
            return False
        needle = _fold(self._search.strip())
        return not needle or needle in _fold(p.name) or needle in _fold(p.description)
