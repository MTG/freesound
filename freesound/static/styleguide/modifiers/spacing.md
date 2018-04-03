A set of classes `v-spacing-$i` and `h-spacing-$i` is available to make it easy to achieve consistent spacing.
`$i` must in `[1, 7]` and the greater its value, the greater the spacing.

```jsx
<div>
  <div class="v-spacing-7">Some vertical space between this text and the following buttons</div>
  <div>
    <button class="h-spacing-4 btn-primary">Horizontal spaced from Other button</button>
    <button class="btn-secondary">Other button</button>
  </div>
</div>
```

Also the classes `v-padding-$i` and `h-padding-$i` are available for the same purpose, but related to padding:

```jsx
<div>
  <div class="v-spacing-3">
    <div class="border-grey-light">No padding</div>
  </div>
  <div class="v-spacing-3">
    <div class="border-grey-light h-padding-3 v-padding-2">Some padding</div>
  </div>
  <div class="v-spacing-3">
    <div class="border-grey-light h-padding-7 v-padding-7">A LOT OF padding</div>
  </div>
</div>
```

TIP: You can also use `.padding-$i` and `.spacing-$i` as a shortcut when you want to apply the same spacing/padding value for horizontal and vertical axis for the same element.
