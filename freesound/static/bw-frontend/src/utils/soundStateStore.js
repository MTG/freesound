// Map-of-Sets store for per-sound transient flags (added/remove/featured)
// on the collection edit page. Sounds aren't actually added or removed until
// the form is submitted; this tracks the pending state in the meantime.
class SoundStateStore {
  // ``actionNames`` is e.g. ['added', 'remove', 'featured']. Each becomes a
  // Set<id> tracking which sounds carry that flag. ``this.actionNames`` is
  // exposed (frozen) for callers that need to enumerate them.
  constructor(actionNames = [], { maxFeatured = Infinity } = {}) {
    this._meta = new Map(); // id → metadata (also "known ids")
    this._sets = new Map(); // actionName → Set<id>
    this._listeners = [];
    this.maxFeatured = maxFeatured;

    actionNames.forEach(name => this._sets.set(name, new Set()));
    this.actionNames = Object.freeze([...actionNames]);
  }

  // Bulk-init: register sounds, then apply { actionName: [ids] }.
  load(soundsArray, flagged = {}) {
    soundsArray.forEach(s => this._meta.set(s.id, s));
    for (const [name, ids] of Object.entries(flagged)) {
      const set = this._sets.get(name);
      if (set) {
        ids.forEach(id => {
          if (this._meta.has(id)) set.add(id);
        });
      }
    }
    return this;
  }

  // Register a newly-added sound with the 'added' flag and notify listeners.
  add(id, meta) {
    if (!this._meta.has(id)) {
      this._meta.set(id, meta);
      const added = this._sets.get('added');
      if (added) {
        added.add(id);
        this._notify(id, 'added', true);
      }
    }
    return this;
  }

  featuredCount() {
    const featured = this._sets.get('featured');
    if (!featured) return 0;
    const removed = this._sets.get('remove');
    if (!removed || removed.size === 0) return featured.size;
    let count = 0;
    for (const id of featured) {
      if (!removed.has(id)) count++;
    }
    return count;
  }

  // Returns the new active state, or undefined if action/id isn't tracked.
  // Returns undefined (no-op) when featuring would exceed the limit.
  toggleAction(id, name) {
    const set = this._sets.get(name);
    if (!set || !this._meta.has(id)) return undefined;
    const active = !set.has(id);
    if (active && name === 'featured' && this.featuredCount() >= this.maxFeatured) {
      return undefined;
    }
    if (active) set.add(id);
    else set.delete(id);
    this._notify(id, name, active);
    return active;
  }

  has(id, name) {
    const set = this._sets.get(name);
    return set ? set.has(id) : false;
  }

  ids() {
    return Array.from(this._meta.keys());
  }

  // Tracked sounds minus those with the 'remove' flag set.
  presentCount() {
    const removed = this._sets.get('remove');
    return this._meta.size - (removed ? removed.size : 0);
  }

  // All ids carrying ``name``. Pass excludeRemoved=true to skip removed sounds.
  idsWithAction(name, excludeRemoved = false) {
    const set = this._sets.get(name);
    if (!set) return [];
    const removed = excludeRemoved ? this._sets.get('remove') : null;
    if (!removed || removed.size === 0) return Array.from(set);
    const result = [];
    for (const id of set) {
      if (!removed.has(id)) result.push(id);
    }
    return result;
  }

  allSoundsWithMeta() {
    return Array.from(this._meta.values());
  }

  onChange(listener) {
    this._listeners.push(listener);
    return this;
  }

  _notify(id, name, active) {
    this._listeners.forEach(fn => fn(id, name, active));
  }
}

export { SoundStateStore };
