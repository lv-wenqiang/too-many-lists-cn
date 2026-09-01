# IterMut

说实话，IterMut 简直离谱。 Which in itself seems like a wild
thing to say; surely it's identical to Iter!

Semantically, yes, but 这个 nature of 共享 and 可变 references means
that Iter 是 "trivial" while IterMut 是 Legit Wizard Magic.

这个 key insight comes 从 our 实现 of Iterator for Iter:

```rust ,ignore
impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> { /* stuff */ }
}
```

Which 可以 be desugared to:

```rust ,ignore
impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next<'b>(&'b mut self) -> Option<&'a T> { /* stuff */ }
}
```

这个 signature of `next` establishes *no* constraint between 这个 生命周期
of 这个 输入 and 这个 输出! Why do 我们 care? It means 我们 可以 call `next`
反复 and 反复 unconditionally!


```rust ,ignore
let mut list = List::new();
list.push(1); list.push(2); list.push(3);

let mut iter = list.iter();
let x = iter.next().unwrap();
let y = iter.next().unwrap();
let z = iter.next().unwrap();
```

酷！

这 是 *definitely 没问题* for 共享 references 因为 这个 whole point 是 that
你 可以 have tons of them at once. However 可变 references *can't* coexist.
这个 whole point 是 that they're exclusive.

这个 end result 是 that it's notably harder to 写出 IterMut 使用 安全
代码 (and 我们 haven't gotten 进入 什么 that even means yet...). Surprisingly,
IterMut 可以 实际上 be implemented for many structures completely safely!

We'll start by 只是 taking 这个 Iter 代码 and changing everything to be 可变:

```rust ,ignore
pub struct IterMut<'a, T> {
    next: Option<&'a mut Node<T>>,
}

impl<T> List<T> {
    pub fn iter_mut(&self) -> IterMut<'_, T> {
        IterMut { next: self.head.as_deref_mut() }
    }
}

impl<'a, T> Iterator for IterMut<'a, T> {
    type Item = &'a mut T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.as_deref_mut();
            &mut node.elem
        })
    }
}
```

```text
> cargo build
error[E0596]: cannot borrow `self.head` as mutable, as it is behind a `&` reference
  --> src/second.rs:95:25
   |
94 |     pub fn iter_mut(&self) -> IterMut<'_, T> {
   |                     ----- help: consider changing this to be a mutable reference: `&mut self`
95 |         IterMut { next: self.head.as_deref_mut() }
   |                         ^^^^^^^^^ `self` is a `&` reference, so the data it refers to cannot be borrowed as mutable

error[E0507]: cannot move out of borrowed content
   --> src/second.rs:103:9
    |
103 |         self.next.map(|node| {
    |         ^^^^^^^^^ cannot move out of borrowed content
```

Ok looks like we've got two 不同 errors here. 这个 首先 one looks 非常 清楚
though, it even tells us 如何 to fix it! 你 can't upgrade a 共享 引用 to a 可变
one, so `iter_mut` needs to take `&mut self`. Just a silly copy-paste 错误.

```rust ,ignore
pub fn iter_mut(&mut self) -> IterMut<'_, T> {
    IterMut { next: self.head.as_deref_mut() }
}
```

What about 这个 其他 one?

糟糕！ I 实际上 accidentally made an 错误 当 writing 这个 `iter` impl in
这个 previous section, and 我们 were 只是 getting lucky that it worked!

我们 have 只是 had our 首先 run in 使用 这个 magic of Copy. When 我们 introduced [所有权][所有权] 我们
said that 当 你 move stuff, 你 can't use it anymore. For 一些 types, 这
makes perfect sense. Our 好 friend Box manages an allocation on 这个 heap for
us, and 我们 certainly don't 想要 two pieces of 代码 to think that they 需要 to
free its memory.

However for 其他 types 这 是 *garbage*. Integers have no
所有权 semantics; they're 只是 meaningless numbers! 这 是 为什么 integers 是
marked as Copy. Copy types 是 known to be perfectly copyable by a bitwise copy.
As such, they have a super power: 当 moved, 这个 旧 值 *是* 仍然 usable.
As a consequence, 你 可以 even move a Copy type 出 of a 引用 不使用
replacement!

All numeric primitives in Rust (i32, u64, bool, f32, char, etc...) 是 Copy.
你 可以 也 declare any user-defined type to be Copy as well, as long as
所有 its components 是 Copy.

Critically to 为什么 这 代码 was working, 共享 references 是 也 Copy!
Because `&` 是 copy, `Option<&>` 是 *也* Copy. So 当 我们 did `self.next.map` it
was 没问题 因为 这个 Option was 只是 copied. Now 我们 can't do that, 因为
`&mut` isn't Copy (if 你 copied an &mut, you'd have two &mut's to 这个 相同
location in memory, which 是 forbidden). Instead, 我们 应该 properly `take`
这个 Option to get it.


```rust ,ignore
fn next(&mut self) -> Option<Self::Item> {
    self.next.take().map(|node| {
        self.next = node.next.as_deref_mut();
        &mut node.elem
    })
}
```

```text
> cargo build

```

呃……哇。我的天！IterMut 居然直接就能工作！

测试一下：


```rust ,ignore
#[test]
fn iter_mut() {
    let mut list = List::new();
    list.push(1); list.push(2); list.push(3);

    let mut iter = list.iter_mut();
    assert_eq!(iter.next(), Some(&mut 3));
    assert_eq!(iter.next(), Some(&mut 2));
    assert_eq!(iter.next(), Some(&mut 1));
}
```

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 6 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::iter_mut ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::peek ... ok

test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured

```

没错，它能工作。

Holy shit.

什么。

Ok I mean it 实际上 *是* supposed to 工作, but there's usually something
stupid that gets in 这个 way! 这里需要明确一点：

我们 have 只是 implemented a piece of 代码 that takes a singly-linked 列表, and
returns a 可变 引用 to 每个 single 元素 in 这个 列表 at most once.
And it's statically verified to do that. And it's totally 安全. And 我们 didn't
have to do anything wild.

依我看，这可是件大事。 There 是 a couple reasons 为什么
这 工作:

* 我们 `take` 这个 `Option<&mut>` so 我们 have exclusive access to 这个 可变
  引用. No 需要 to worry about someone looking at it 再次.
* Rust understands that it's ok to shard a 可变 引用 进入 这个 subfields
  of 这个 pointed-to struct, 因为 there's no way to "go back up", and they're
  definitely disjoint.

事实证明，这个基本思路也可以应用于 to get a 安全 IterMut for an
array or a tree as well! 你 可以 even make 这个 迭代器 DoubleEnded, so that
你 可以 consume 这个 迭代器 从 这个 front *and* 这个 back at once! 哇！

[所有权]: first-ownership.md
