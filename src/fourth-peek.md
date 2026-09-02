# 查看（peek）

好了，我们熬过了`push`和`pop`。不骗你，刚才那段有点情绪上头。
编译期正确性真是一剂猛药。

我们来做点简单的事情降降温：实现`peek_front`就行了。
这事儿以前一直都特别容易。现在肯定还是很容易，对吧？

对吧？

事实上，我觉得我直接复制粘贴就行了！

```rust ,ignore
pub fn peek_front(&self) -> Option<&T> {
    self.head.as_ref().map(|node| {
        &node.elem
    })
}
```

等等。这次不行。

```rust ,ignore
pub fn peek_front(&self) -> Option<&T> {
    self.head.as_ref().map(|node| {
        // BORROW!!!!
        &node.borrow().elem
    })
}
```

哈。

```text
cargo build

error[E0515]: cannot return value referencing temporary value
  --> src/fourth.rs:66:13
   |
66 |             &node.borrow().elem
   |             ^   ----------^^^^^
   |             |   |
   |             |   temporary value created here
   |             |
   |             returns a value referencing data owned by the current function
```

行吧，我这就去把电脑烧了。

这跟我们的单向链表栈是一模一样的逻辑。为什么结果不一样。为什么啊。

答案其实就是本章的全部寓意：RefCell 让一切都变得悲伤。到目前为止，
RefCell 还只是个麻烦。现在它们要变成噩梦了。

那到底出了什么事？要搞明白这一点，我们得回到`borrow`的定义：

```rust ,ignore
fn borrow<'a>(&'a self) -> Ref<'a, T>
fn borrow_mut<'a>(&'a self) -> RefMut<'a, T>
```

在布局那一节里我们说过：

> RefCell 不是在静态层面强制这些规则，而是在运行时强制它们。
> 如果你破坏了规则，RefCell 就会直接 panic 并让程序崩溃。
> 它为什么要返回 Ref 和 RefMut 这些东西呢？嗯，它们的行为基本上就像是
> 借用版的`Rc`。它们还会让 RefCell 一直保持被借用状态，直到它们离开作用域。
> **这个我们后面再说。**

现在就是后面了。

`Ref`和`RefMut`分别实现了`Deref`和`DerefMut`。所以在绝大多数意义上，
它们的行为*完全*就像`&T`和`&mut T`。然而，由于这些 trait 的工作方式，
返回的那个引用是和 Ref 的生命周期绑定的，而不是和真正的 RefCell 绑定。
这意味着只要我们还留着那个引用，Ref 就必须一直杵在那儿。

这实际上是保证正确性所必需的。当一个 Ref 被丢弃时，它会告诉 RefCell
自己不再借用了。所以如果我们*真的*设法让引用活得比 Ref 还久，
那我们就可能在还有引用在外面晃悠的时候拿到一个 RefMut，
把 Rust 的类型系统彻底掰成两半。

那这让我们陷入了什么境地呢？我们只想返回一个引用，却又必须让这个 Ref
留在身边。可是一旦我们从`peek`里把引用返回出去，函数就结束了，
`Ref`也就离开了作用域。

😖

据我所知，我们在这里其实是彻底没辙了。你没法那样把 RefCell 的使用完全封装起来。

但是……如果我们干脆放弃完全隐藏实现细节呢？如果我们就返回 Ref 呢？

```rust ,ignore
pub fn peek_front(&self) -> Option<Ref<T>> {
    self.head.as_ref().map(|node| {
        node.borrow()
    })
}
```

```text
> cargo build

error[E0412]: cannot find type `Ref` in this scope
  --> src/fourth.rs:63:40
   |
63 |     pub fn peek_front(&self) -> Option<Ref<T>> {
   |                                        ^^^ not found in this scope
help: possible candidates are found in other modules, you can import them into scope
   |
1  | use core::cell::Ref;
   |
1  | use std::cell::Ref;
   |
```

噗。得导入点东西。


```rust ,ignore
use std::cell::{Ref, RefCell};
```

```text
> cargo build

error[E0308]: mismatched types
  --> src/fourth.rs:64:9
   |
64 | /         self.head.as_ref().map(|node| {
65 | |             node.borrow()
66 | |         })
   | |__________^ expected type parameter, found struct `fourth::Node`
   |
   = note: expected type `std::option::Option<std::cell::Ref<'_, T>>`
              found type `std::option::Option<std::cell::Ref<'_, fourth::Node<T>>>`
```

嗯……没错。我们有的是`Ref<Node<T>>`，而我们想要的是`Ref<T>`。我们可以放弃
封装的一切念想，直接把它返回出去。我们也可以把事情搞得更复杂，
把`Ref<Node<T>>`包进一个新类型里，只暴露对`&T`的访问。

这两个选项都*有点*逊。

所以我们要往更深处走。来找点*乐子*。我们的乐子来源是*这头猛兽*：

```rust ,ignore
map<U, F>(orig: Ref<'b, T>, f: F) -> Ref<'b, U>
    where F: FnOnce(&T) -> &U,
          U: ?Sized
```

> 为所借用数据的某个组成部分创建一个新的 Ref。

没错：就像你可以在 Option 上做 map 一样，你也可以在 Ref 上做 map。

我敢肯定某个地方有人会因为*单子*之类的东西而兴奋不已，但那些我一概不关心。
另外我也不觉得它是个正经的单子，因为这里没有类似 None 的情形，不过我扯远了。

它很酷，对我来说这就够了。*我需要它*。

```rust ,ignore
pub fn peek_front(&self) -> Option<Ref<T>> {
    self.head.as_ref().map(|node| {
        Ref::map(node.borrow(), |node| &node.elem)
    })
}
```

```text
> cargo build
```

啊——爽——

我们把栈的那个测试改吧改吧，确认一下这玩意儿能用。因为 Ref 没有实现比较操作，
所以得改动几下。

```rust ,ignore
#[test]
fn peek() {
    let mut list = List::new();
    assert!(list.peek_front().is_none());
    list.push_front(1); list.push_front(2); list.push_front(3);

    assert_eq!(&*list.peek_front().unwrap(), &3);
}
```


```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 10 tests
test first::test::basics ... ok
test fourth::test::basics ... ok
test second::test::basics ... ok
test fourth::test::peek ... ok
test second::test::iter_mut ... ok
test second::test::into_iter ... ok
test third::test::basics ... ok
test second::test::peek ... ok
test second::test::iter ... ok
test third::test::iter ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured

```

太好了！
