# 构建

好了，我们从构建链表开始。在这套新体系下，这相当直截了当。
`new`仍然平淡无奇，把所有字段都置为 None 就行。另外，因为代码开始有点笨重了，
我们顺手把 Node 的构造函数也拆出来：

```rust ,ignore
impl<T> Node<T> {
    fn new(elem: T) -> Rc<RefCell<Self>> {
        Rc::new(RefCell::new(Node {
            elem: elem,
            prev: None,
            next: None,
        }))
    }
}

impl<T> List<T> {
    pub fn new() -> Self {
        List { head: None, tail: None }
    }
}
```

```text
> cargo build

**A BUNCH OF DEAD CODE WARNINGS BUT IT BUILT**
```

好耶！

现在我们来试着写往链表头部压入的操作。因为双向链表要复杂得多，
我们得多干不少活。单向链表的操作能被压缩成轻松的一行，
而双向链表的操作则相当复杂。

具体来说，我们现在需要特别处理围绕空链表的一些边界情况。大多数操作只会碰
`head`或`tail`指针。然而在从空链表转换出去、或者转换回空链表时，
我们需要同时改动*两个*。

有一个简单的办法可以验证我们的方法是否说得通：看我们是否维持了下面这个不变式，
即每个节点都应该恰好有两个指向它的指针。链表中间的每个节点都被它的前驱和后继
指着，而两端的节点则被链表本身指着。

我们来试一把：

```rust ,ignore
pub fn push_front(&mut self, elem: T) {
    // new node needs +2 links, everything else should be +0
    let new_head = Node::new(elem);
    match self.head.take() {
        Some(old_head) => {
            // non-empty list, need to connect the old_head
            old_head.prev = Some(new_head.clone()); // +1 new_head
            new_head.next = Some(old_head);         // +1 old_head
            self.head = Some(new_head);             // +1 new_head, -1 old_head
            // total: +2 new_head, +0 old_head -- OK!
        }
        None => {
            // empty list, need to set the tail
            self.tail = Some(new_head.clone());     // +1 new_head
            self.head = Some(new_head);             // +1 new_head
            // total: +2 new_head -- OK!
        }
    }
}
```

```text
cargo build

error[E0609]: no field `prev` on type `std::rc::Rc<std::cell::RefCell<fourth::Node<T>>>`
  --> src/fourth.rs:39:26
   |
39 |                 old_head.prev = Some(new_head.clone()); // +1 new_head
   |                          ^^^^ unknown field

error[E0609]: no field `next` on type `std::rc::Rc<std::cell::RefCell<fourth::Node<T>>>`
  --> src/fourth.rs:40:26
   |
40 |                 new_head.next = Some(old_head);         // +1 old_head
   |                          ^^^^ unknown field
```

好吧。编译错误。开局不错。开局不错。

为什么我们不能访问节点上的`prev`和`next`字段？之前我们只有`Rc<Node>`的时候
明明是好使的。看起来是`RefCell`在挡道。

我们大概该去查查文档。

*用谷歌搜索“rust refcell”*

*[点击第一个链接](https://doc.rust-lang.org/std/cell/struct.RefCell.html)*

> 一个具有动态检查借用规则的可变内存位置
>
> 更多内容参见[模块级文档](https://doc.rust-lang.org/std/cell/index.html)。

*点击链接*

> 可共享的可变容器。
>
> `Cell<T>`和`RefCell<T>`类型的值可以透过共享引用（也就是常见的`&T`类型）被修改，
> 而大多数 Rust 类型只能透过独占（`&mut T`）引用被修改。我们说`Cell<T>`和
> `RefCell<T>`提供了“内部可变性”，与之相对的是表现出“继承式可变性”的典型
> Rust 类型。
>
> Cell 类型有两种风味：`Cell<T>`和`RefCell<T>`。`Cell<T>`提供`get`和`set`方法，
> 只需一次方法调用就能改变内部的值。不过`Cell<T>`只兼容那些实现了`Copy`的类型。
> 对于其他类型，则必须使用`RefCell<T>`类型，在修改之前先获取一个写锁。
>
> `RefCell<T>`利用 Rust 的生命周期实现了“动态借用”，这个过程让人可以宣称自己
> 对内部值拥有临时的、独占的、可变的访问权。`RefCell<T>`的借用是“在运行时”被
> 追踪的，这与 Rust 原生的引用类型不同，后者完全是在编译期静态追踪的。因为
> `RefCell<T>`的借用是动态的，所以有可能试图借用一个已经被可变借用的值；
> 当这种情况发生时，就会导致线程 panic。
>
> # 何时选择内部可变性
>
> 更常见的继承式可变性——即必须拥有独占访问权才能修改一个值——是让 Rust 能够
> 对指针别名进行强有力推理、从静态层面预防崩溃缺陷的关键语言要素之一。正因如此，
> 继承式可变性是首选，而内部可变性多少算是最后的手段。不过既然 cell 类型能在
> 本来不被允许的地方开启修改能力，那么在某些场合内部可变性可能是恰当的，
> 甚至*必须*被使用，例如：
>
> * 为共享类型引入继承式可变性的根。
> * 逻辑上不可变的方法的实现细节。
> * 会进行修改的`Clone`实现。
>
> ## 为共享类型引入继承式可变性的根
>
> 共享智能指针类型，包括`Rc<T>`和`Arc<T>`，提供了可以被克隆并在多方之间共享的
> 容器。因为其中包含的值可能存在多重别名，所以它们只能作为共享引用被借用，
> 而不能作为可变引用。如果没有 cell，就根本不可能修改共享 box 内部的数据！
>
> 因此，把`RefCell<T>`放进共享指针类型里以重新引入可变性，是非常常见的做法：
>
> ```rust ,ignore
> use std::collections::HashMap;
> use std::cell::RefCell;
> use std::rc::Rc;
>
> fn main() {
>     let shared_map: Rc<RefCell<_>> = Rc::new(RefCell::new(HashMap::new()));
>     shared_map.borrow_mut().insert("africa", 92388);
>     shared_map.borrow_mut().insert("kyoto", 11837);
>     shared_map.borrow_mut().insert("piccadilly", 11826);
>     shared_map.borrow_mut().insert("marbles", 38);
> }
> ```
>
> 注意这个例子用的是`Rc<T>`而不是`Arc<T>`。`RefCell<T>`是给单线程场景用的。
> 如果你在多线程场景下需要共享的可变性，请考虑使用`Mutex<T>`。

嘿，Rust 的文档一如既往地棒极了。

我们真正关心的干货是这一行：

```rust ,ignore
shared_map.borrow_mut().insert("africa", 92388);
```

尤其是那个`borrow_mut`。看起来我们需要显式地借用 RefCell。`.`运算符不会
替我们代劳。真怪。来试试：

```rust ,ignore
pub fn push_front(&mut self, elem: T) {
    let new_head = Node::new(elem);
    match self.head.take() {
        Some(old_head) => {
            old_head.borrow_mut().prev = Some(new_head.clone());
            new_head.borrow_mut().next = Some(old_head);
            self.head = Some(new_head);
        }
        None => {
            self.tail = Some(new_head.clone());
            self.head = Some(new_head);
        }
    }
}
```


```text
> cargo build

warning: field is never used: `elem`
  --> src/fourth.rs:12:5
   |
12 |     elem: T,
   |     ^^^^^^^
   |
   = note: #[warn(dead_code)] on by default
```

嘿，它编译过了！文档再次获胜。
