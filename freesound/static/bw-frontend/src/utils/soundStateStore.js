class SoundStateStore {
    /**
     * @param {string[]} [actionNames] - e.g. ['added', 'remove', 'featured'].
     *   Bitmask flags are auto-assigned (1, 2, 4, …) and exposed via this.FLAG
     *   using uppercased keys (ADDED, REMOVE, FEATURED).
     */
    constructor(actionNames = []) {
        this._states = new Map();   // id → bitmask
        this._meta = new Map();     // id → metadata object
        this._actions = new Map();  // actionName → { flag }
        this._listeners = [];

        const flags = {};
        actionNames.forEach((name, i) => {
            const flag = 1 << i;
            flags[name.toUpperCase()] = flag;
            this._actions.set(name, { flag });
        });
        this.FLAG = Object.freeze(flags);
    }

    _actionFlag(name) {
        const action = this._actions.get(name);
        return action ? action.flag : 0;
    }

    // ─── Registration ─────────────────────────────────────────

    /**
     * Bulk-initialise: track all sounds, set their metadata, and apply initial flags.
     * @param {Object[]} soundsArray - objects with at least an `id` property
     * @param {Object}  [flagged]    - { actionName: [id, …] } initial flags to set
     */
    load(soundsArray, flagged = {}) {
        soundsArray.forEach(s => {
            this._states.set(s.id, 0);
            this._meta.set(s.id, s);
        });
        for (const [actionName, ids] of Object.entries(flagged)) {
            const flag = this._actionFlag(actionName);
            if (flag) ids.forEach(id => {
                if (this._states.has(id)) this._states.set(id, this._states.get(id) | flag);
            });
        }
        return this;
    }

    /** Register a newly added object with the ADDED flag and notify listeners. */
    add(id, meta) {
        if (!this._states.has(id)) {
            if (meta) this._meta.set(id, meta);
            const flag = this._actionFlag('added');
            this._states.set(id, flag);
            if (flag) this._notify(id, flag, true);
        }
        return this;
    }

    // ─── State mutation ────────────────────────────────────────

    toggleAction(id, actionName) {
        const action = this._actions.get(actionName);
        if (!action || !this._states.has(id)) return undefined;
        const active = !this.hasFlag(id, action.flag);
        const mask = this._states.get(id);
        this._states.set(id, active ? mask | action.flag : mask & ~action.flag);
        this._notify(id, action.flag, active);
        return active;
    }

    // ─── Queries ──────────────────────────────────────────────

    hasFlag(id, flag) {
        const mask = this._states.has(id) ? this._states.get(id) : 0;
        return (mask & flag) !== 0;
    }

    _entries(excludeRemoved = false) {
        const removedFlag = excludeRemoved ? this._actionFlag('remove') : 0;
        return Array.from(this._states.entries())
            .filter(([, mask]) => !removedFlag || (mask & removedFlag) === 0);
    }

    /** All tracked object IDs. */
    ids() {
        return Array.from(this._states.keys());
    }

    /** Count of objects where REMOVED is NOT set. */
    presentCount() {
        return this._entries(true).length;
    }

    /** Object IDs where the given flag is set. Pass excludeRemoved=true to omit removed objects. */
    idsWithFlag(flag, excludeRemoved = false) {
        return this._entries(excludeRemoved)
            .filter(([, mask]) => (mask & flag) !== 0)
            .map(([id]) => id);
    }

    // ─── Metadata ──────────────────────────────────────────────

    allSoundsWithMeta() {
        return this.ids()
            .map(id => this._meta.get(id))
            .filter(Boolean);
    }

    // ─── Listeners ────────────────────────────────────────────

    onChange(listener) {
        this._listeners.push(listener);
        return this;
    }

    removeListener(listener) {
        const idx = this._listeners.indexOf(listener);
        if (idx !== -1) this._listeners.splice(idx, 1);
        return this;
    }

    _notify(id, flag, active) {
        this._listeners.forEach(fn => fn(id, flag, active));
    }

    // ─── Action registry ──────────────────────────────────────

    /** Returns registered actions as [{ actionName, flag }]. */
    actions() {
        return Array.from(this._actions.entries(), ([actionName, { flag }]) => ({ actionName, flag }));
    }
}

export { SoundStateStore };
