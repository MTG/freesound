Home, not logged in, expanded: (the ellipsis icon and the dropdowns won't load correctly inside styleguidist)

```jsx
<nav class="bw-nav bw-nav--home bw-nav--expanded container">
  <div class="bw-nav__logo-search-container">
    <div class="bw-nav__logo">
      <a href="" class="no-hover" />
    </div>
    <div class="input-wrapper">
      <input type="search" class="bw-nav__search" placeholder="Search sounds..." />
    </div>
  </div>
  <ul class="bw-nav__actions">
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Sounds
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Packs
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Forum
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Map
      </a>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu dropdown-toggle no-hover"
        id="three-dots-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      />
      <ul class="dropdown-menu" aria-labelledby="three-dots-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Tags
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Charts
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donors
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Help
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Developers
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Blog
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Labs
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound t-Shirt
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--black" href="">
        Log in
      </a>
    </li>
    <button class="btn-primary">Join</button>
  </ul>
</nav>
```

Home, logged in, expanded (with notifications):

```jsx
<nav class="bw-nav bw-nav--home bw-nav--expanded container">
  <div class="bw-nav__logo-search-container">
    <div class="bw-nav__logo">
      <a href="" class="no-hover" />
    </div>
    <div class="input-wrapper">
      <input type="search" class="bw-nav__search" placeholder="Search sounds..." />
    </div>
  </div>
  <ul class="bw-nav__actions">
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Sounds
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Packs
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Forum
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Map
      </a>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu dropdown-toggle no-hover"
        id="three-dots-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      />
      <ul class="dropdown-menu" aria-labelledby="three-dots-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Tags
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Charts
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donors
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Help
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Developers
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Blog
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Labs
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound t-Shirt
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu--avatar bw-nav__menu--avatar-with-notifications dropdown-toggle no-hover"
        id="avatar-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      >
        <img src="avatar.jpg" />
      </a>
      <ul class="dropdown-menu" aria-labelledby="avatar-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            View profile
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Manage uploads
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Bookmarks
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            My messages
            <span class="text-red">(3)</span>
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Account settings
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Manage API settings
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donate
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--grey" href="">
            Logout
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action">
      <button class="btn-secondary">Donate</button>
    </li>
    <li class="bw-nav__action">
      <button class="btn-primary">Upload sound</button>
    </li>
  </ul>
</nav>
```

Home, logged in, expanded (no notifications):

```jsx
<nav class="bw-nav bw-nav--home bw-nav--expanded container">
  <div class="bw-nav__logo-search-container">
    <div class="bw-nav__logo">
      <a href="" class="no-hover" />
    </div>
    <div class="input-wrapper">
      <input type="search" class="bw-nav__search" placeholder="Search sounds..." />
    </div>
  </div>
  <ul class="bw-nav__actions">
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Sounds
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Packs
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Forum
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Map
      </a>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu dropdown-toggle no-hover"
        id="three-dots-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      />
      <ul class="dropdown-menu" aria-labelledby="three-dots-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Tags
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Charts
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donors
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Help
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Developers
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Blog
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Labs
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound t-Shirt
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu--avatar dropdown-toggle no-hover"
        id="avatar-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      >
        <img src="avatar.jpg" />
      </a>
      <ul class="dropdown-menu" aria-labelledby="avatar-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            View profile
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Manage uploads
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Bookmarks
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            My messages
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Account settings
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Manage API settings
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donate
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--grey" href="">
            Logout
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action">
      <button class="btn-secondary">Donate</button>
    </li>
    <li class="bw-nav__action">
      <button class="btn-primary">Upload sound</button>
    </li>
  </ul>
</nav>
```

Home, not logged in, non-expanded:

```jsx
require('../../src/components/navbar');

<nav class="bw-nav bw-nav--home container">
  <div class="bw-nav__logo-search-container">
    <div class="bw-nav__logo">
      <a href="" class="no-hover" />
    </div>
    <div class="input-wrapper">
      <input type="search" class="bw-nav__search" placeholder="Search sounds..." />
    </div>
  </div>
  <ul class="bw-nav__actions">
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Sounds
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Packs
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Forum
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Map
      </a>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu dropdown-toggle no-hover"
        id="three-dots-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      />
      <ul class="dropdown-menu" aria-labelledby="three-dots-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Tags
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Charts
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donors
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Help
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Developers
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Blog
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Labs
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound t-Shirt
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--black" href="">
        Log in
      </a>
    </li>
    <button class="btn-primary">Join</button>
  </ul>
</nav>;
```

Home, not logged in, non-expanded:

```jsx
<nav class="bw-nav bw-nav--home container">
  <div class="bw-nav__logo-search-container">
    <div class="bw-nav__logo">
      <a href="" class="no-hover" />
    </div>
    <div class="input-wrapper">
      <input type="search" class="bw-nav__search" placeholder="Search sounds..." />
    </div>
  </div>
  <ul class="bw-nav__actions">
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Sounds
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Packs
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Forum
      </a>
    </li>
    <li class="bw-nav__action">
      <a class="bw-link--grey" href="">
        Map
      </a>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu dropdown-toggle no-hover"
        id="three-dots-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      />
      <ul class="dropdown-menu" aria-labelledby="three-dots-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Tags
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Charts
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donors
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Help
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Developers
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Blog
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound Labs
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Freesound t-Shirt
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action dropdown">
      <a
        class="bw-link--grey bw-nav__menu--avatar bw-nav__menu--avatar-with-notifications dropdown-toggle no-hover"
        id="avatar-menu"
        aria-haspopup="true"
        aria-expanded="false"
        data-toggle="dropdown"
      >
        <img src="avatar.jpg" />
      </a>
      <ul class="dropdown-menu" aria-labelledby="avatar-menu">
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            View profile
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Manage uploads
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Bookmarks
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            My messages
            <span class="text-red">(3)</span>
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Account settings
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Manage API settings
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--black" href="">
            Donate
          </a>
        </li>
        <li class="bw-nav__action dropdown-item">
          <a class="bw-link--grey" href="">
            Logout
          </a>
        </li>
      </ul>
    </li>
    <li class="bw-nav__action">
      <button class="btn-secondary">Donate</button>
    </li>
    <li class="bw-nav__action">
      <button class="btn-primary">Upload sound</button>
    </li>
  </ul>
</nav>
```
