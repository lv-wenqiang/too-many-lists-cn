# 布局

好了，回到画板前重新设计布局。

持久化链表最重要的一点，是你可以近乎免费地摆弄链表的尾部：

举个例子，下面这种操作在持久化链表里并不少见：

```text
list1 = A -> B -> C -> D
list2 = tail(list1) = B -> C -> D
list3 = push(list2, X) = X -> B -> C -> D
```

但最终我们希望内存看起来是这样的：

```text
list1 -> A ---+
              |
              v
list2 ------> B -> C -> D
              ^
              |
list3 -> X ---+
```

这用 Box 是根本做不到的，因为`B`的所有权是*共享*的。谁该来释放它呢？
如果我丢弃 list2，它会释放 B 吗？如果用 box，我们当然会指望它这么干！

函数式语言 &mdash; 实际上几乎所有其他语言 &mdash; 都靠*垃圾回收*来绕开这个问题。
有了垃圾回收的魔法，B 只会在所有人都不再看它之后才被释放。万岁！

Rust 没有这些语言所拥有的那种垃圾回收器。它们有*追踪式* GC，会在运行时
翻遍所有还留着的内存，自动算出哪些是垃圾。而 Rust 今天所拥有的，只有
*引用计数*。引用计数可以看作一种非常简单的 GC。在许多负载下，它的吞吐量
显著低于追踪式回收器，而且一旦你造出了环，它就彻底歇菜。但没办法，我们
就只有这个了！好在，对我们的用例来说，永远不会碰到环
（欢迎你自己去证明这一点 &mdash; 反正我是不会证的）。

那么，我们要怎么做引用计数式的垃圾回收呢？用`Rc`！Rc 就像 Box 一样，
但我们可以复制它，而它的内存*只有*在所有由它派生出来的 Rc 都被丢弃之后
才会被释放。不幸的是，这种灵活性有着严重的代价：我们只能拿到指向其内部的
共享引用。这意味着我们永远没法真正把数据从链表里取出来，也没法修改它们。

那我们的布局会长什么样呢？之前我们有：

```rust ,ignore
pub struct List<T> {
    head: Link<T>,
}

type Link<T> = Option<Box<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}
```

我们能不能直接把 Box 换成 Rc？

```rust ,ignore
// in third.rs

pub struct List<T> {
    head: Link<T>,
}

type Link<T> = Option<Rc<Node<T>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
}
```

```text
cargo build

error[E0412]: cannot find type `Rc` in this scope
 --> src/third.rs:5:23
  |
5 | type Link<T> = Option<Rc<Node<T>>>;
  |                       ^^ not found in this scope
help: possible candidate is found in another module, you can import it into scope
  |
1 | use std::rc::Rc;
  |
```

哎哟，扎心了。跟我们写可变链表时用的那些东西不同，Rc 逊到连每个 Rust 程序
都不会隐式导入它。*真是个卢瑟*。

```rust ,ignore
use std::rc::Rc;
```

```text
cargo build

warning: field is never used: `head`
 --> src/third.rs:4:5
  |
4 |     head: Link<T>,
  |     ^^^^^^^^^^^^^
  |
  = note: #[warn(dead_code)] on by default

warning: field is never used: `elem`
  --> src/third.rs:10:5
   |
10 |     elem: T,
   |     ^^^^^^^

warning: field is never used: `next`
  --> src/third.rs:11:5
   |
11 |     next: Link<T>,
   |     ^^^^^^^^^^^^^
```

看着挺靠谱。Rust 依然*完全*不难写嘛。我打赌我们只要把 Box 全局替换成 Rc
就可以收工了！

……

不。不，我们不能。
