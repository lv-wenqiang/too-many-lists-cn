# 布局

我们这套设计的关键是`RefCell`类型。RefCell 的核心是一对方法：

```rust ,ignore
fn borrow(&self) -> Ref<'_, T>;
fn borrow_mut(&self) -> RefMut<'_, T>;
```

`borrow`和`borrow_mut`的规则和`&`与`&mut`的规则完全一样：
你想调用多少次`borrow`都行，但`borrow_mut`要求独占。

RefCell 不是在静态层面强制这些规则，而是在运行时强制它们。
如果你破坏了规则，RefCell 就会直接 panic 并让程序崩溃。
它为什么要返回 Ref 和 RefMut 这些东西呢？嗯，它们的行为基本上就像是
借用版的`Rc`。它们还会让 RefCell 一直保持被借用状态，直到它们离开作用域。
这个我们后面再说。

现在有了 Rc 和 RefCell，我们就能变成……一门啰嗦得离谱、到处都能改、
还回收不了环的垃圾回收语言！耶——耶啊啊啊……

好了，我们想要*双向*链接。这意味着每个节点都有指向前一个和后一个节点的指针。
另外，链表本身也持有指向第一个和最后一个节点的指针。这让我们在链表的*两端*
都能快速插入和删除。

所以我们大概想要这样的东西：

```rust ,ignore
use std::rc::Rc;
use std::cell::RefCell;

pub struct List<T> {
    head: Link<T>,
    tail: Link<T>,
}

type Link<T> = Option<Rc<RefCell<Node<T>>>>;

struct Node<T> {
    elem: T,
    next: Link<T>,
    prev: Link<T>,
}
```

```text
> cargo build

warning: field is never used: `head`
 --> src/fourth.rs:5:5
  |
5 |     head: Link<T>,
  |     ^^^^^^^^^^^^^
  |
  = note: #[warn(dead_code)] on by default

warning: field is never used: `tail`
 --> src/fourth.rs:6:5
  |
6 |     tail: Link<T>,
  |     ^^^^^^^^^^^^^

warning: field is never used: `elem`
  --> src/fourth.rs:12:5
   |
12 |     elem: T,
   |     ^^^^^^^

warning: field is never used: `next`
  --> src/fourth.rs:13:5
   |
13 |     next: Link<T>,
   |     ^^^^^^^^^^^^^

warning: field is never used: `prev`
  --> src/fourth.rs:14:5
   |
14 |     prev: Link<T>,
   |     ^^^^^^^^^^^^^
```

嘿，它编译过了！一堆死代码警告，但它编译过了！我们来试着用一下它。
