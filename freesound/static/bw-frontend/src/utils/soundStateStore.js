import { serializedIdListToIntList } from './data'

// State flags as bitmask constants
const STATE = Object.freeze({
    ADDED: 1 << 0,    // 0001
    REMOVED: 1 << 1,  // 0010
    FEATURED: 1 << 2, // 0100
});

class SoundStateStore {
    /**
     * @param {Object}  config
     * @param {Element} config.input   - hidden input for base object IDs
     * @param {Array<{actionName: string, flag: number, input?: Element}>} config.actions
     */
    constructor(config) {
        this._states = new Map();   // id → bitmask
        this._actions = new Map();  // actionName → { flag, input }
        this._listeners = [];
        this._mainInput = null;

        if (config) this._init(config);
    }

    // ─── Init ─────────────────────────────────────────────────

    _init(config) {
        this._mainInput = config.input || null;

        if (this._mainInput && this._mainInput.value) {
            serializedIdListToIntList(this._mainInput.value).forEach(id => this.track(id));
        }

        (config.actions || []).forEach(({ actionName, flag, input = null }) => {
            this._actions.set(actionName, { flag, input });
            if (input && input.value) {
                serializedIdListToIntList(input.value).forEach(id => this.setFlag(id, flag));
            }
        });
    }

    // ─── Registration ─────────────────────────────────────────

    /** Register an existing object with no flags (silent, no notification). */
    track(id) {
        if (!this._states.has(id)) this._states.set(id, 0);
        return this;
    }

    /** Register a newly added object with the ADDED flag and notify listeners. */
    add(id) {
        if (!this._states.has(id)) {
            this._states.set(id, STATE.ADDED);
            this._notify(id, STATE.ADDED, true);
        }
        return this;
    }

    // ─── State mutation ────────────────────────────────────────

    setFlag(id, flag, active = true) {
        if (!this._states.has(id)) return this;
        const mask = this._states.get(id);
        this._states.set(id, active ? mask | flag : mask & ~flag);
        this._notify(id, flag, active);
        return this;
    }

    toggleFlag(id, flag) {
        if (!this._states.has(id)) return false;
        const active = !this.hasFlag(id, flag);
        this.setFlag(id, flag, active);
        return active;
    }

    toggleAction(id, actionName) {
        const action = this._actions.get(actionName);
        return action ? this.toggleFlag(id, action.flag) : undefined;
    }

    // ─── Queries ──────────────────────────────────────────────

    hasFlag(id, flag) {
        const mask = this._states.has(id) ? this._states.get(id) : 0;
        return (mask & flag) !== 0;
    }

    /** All tracked object IDs. Pass excludeRemoved=true to omit REMOVED objects. */
    ids(excludeRemoved = false) {
        if (!excludeRemoved) return Array.from(this._states.keys());
        return Array.from(this._states.entries())
            .filter(([, mask]) => (mask & STATE.REMOVED) === 0)
            .map(([id]) => id);
    }

    /** Count of objects where REMOVED is NOT set. */
    presentCount() {
        return this.ids(true).length;
    }

    /** Object IDs where the given flag is set. Pass excludeRemoved=true to omit REMOVED objects. */
    idsWithFlag(flag, excludeRemoved = false) {
        return Array.from(this._states.entries())
            .filter(([, mask]) => (mask & flag) !== 0 && (!excludeRemoved || (mask & STATE.REMOVED) === 0))
            .map(([id]) => id);
    }

    // ─── Listeners ────────────────────────────────────────────

    onChange(listener) {
        this._listeners.push(listener);
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

    // ─── Serialization ────────────────────────────────────────

    /**
     * Writes current state back to all associated hidden inputs.
     * ADDED objects are included even if REMOVED so the server keeps returning them.
     */
    syncInputs() {
        if (this._mainInput) {
            this._mainInput.value = this.ids(true).join(',');
        }

        this._actions.forEach(({ flag, input }) => {
            if (input) {
                // ADDED and REMOVED: report faithfully (server reconciles the overlap)
                // Other flags (e.g. FEATURED): exclude sounds that are REMOVED
                const ids = (flag === STATE.ADDED || flag === STATE.REMOVED)
                    ? this.idsWithFlag(flag)
                    : this.idsWithFlag(flag, true);
                input.value = ids.join(',');
            }
        });
    }
}

export { STATE, SoundStateStore };
