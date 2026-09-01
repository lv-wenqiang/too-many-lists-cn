# 拆解

`pop_front`的基本逻辑应该和`push_front`一样，只是反过来。来试试：

```rust ,ignore
pub fn pop_front(&mut self) -> Option<T> {
    // need to take the old head, ensuring it's -2
    self.head.take().map(|old_head| {                         // -1 old
        match old_head.borrow_mut().next.take() {
            Some(new_head) => {                               // -1 new
                // not emptying list
                new_head.borrow_mut().prev.take();            // -1 old
                self.head = Some(new_head);                   // +1 new
                // total: -2 old, +0 new
            }
            None => {
                // emptying list
                self.tail.take();                             // -1 old
                // total: -2 old, (no new)
            }
        }
        old_head.elem
    })
}
```

```text
> cargo build

error[E0609]: no field `elem` on type `std::rc::Rc<std::cell::RefCell<fourth::Node<T>>>`
  --> src/fourth.rs:64:22
   |
64 |             old_head.elem
   |                      ^^^^ unknown field
```

啊。*RefCell 们*。看来又得`borrow_mut`一下了……

```rust ,ignore
pub fn pop_front(&mut self) -> Option<T> {
    self.head.take().map(|old_head| {
        match old_head.borrow_mut().next.take() {
            Some(new_head) => {
                new_head.borrow_mut().prev.take();
                self.head = Some(new_head);
            }
            None => {
                self.tail.take();
            }
        }
        old_head.borrow_mut().elem
    })
}
```

```text
cargo build

error[E0507]: cannot move out of borrowed content
  --> src/fourth.rs:64:13
   |
64 |             old_head.borrow_mut().elem
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^ cannot move out of borrowed content
```

*叹气*

> cannot move out of borrowed content

嗯……看来 Box 是*真的*把我们惯坏了。`borrow_mut`只能给我们一个`&mut Node<T>`，
而我们没法从那里面移出东西！

我们需要某种能接受一个`RefCell<T>`并交给我们一个`T`的东西。
去[文档][refcell]里找找有没有这样的玩意儿：

> `fn into_inner(self) -> T`
>
> 消耗掉这个 RefCell，返回它所包裹的值。

看起来很有戏！

```rust ,ignore
old_head.into_inner().elem
```

```text
> cargo build

error[E0507]: cannot move out of an `Rc`
  --> src/fourth.rs:64:13
   |
64 |             old_head.into_inner().elem
   |             ^^^^^^^^ cannot move out of an `Rc`
```

啊糟。`into_inner`想把 RefCell 移出来，但我们做不到，因为它在一个`Rc`里面。
正如我们在上一章看到的，`Rc<T>`只允许我们拿到指向它内部的共享引用。这说得通，
因为这正是引用计数指针的*全部意义*：它们是共享的！

我们为引用计数链表实现 Drop 的时候也碰到过这个问题，解决办法也一样：
`Rc::try_unwrap`，它会在引用计数为 1 时把 Rc 的内容移出来。

```rust ,ignore
Rc::try_unwrap(old_head).unwrap().into_inner().elem
```

`Rc::try_unwrap`返回一个`Result<T, Rc<T>>`。Result 基本上就是广义的`Option`，
只不过其中的`None`情形还附带了数据。在这个例子里，附带的就是你试图解包的那个
`Rc`。既然我们不关心失败的情形（如果程序写对了，它*必然*成功），
我们就直接对它调用`unwrap`。

不管怎样，来看看我们接下来会拿到什么编译错误吧（面对现实吧，肯定会有一个）。

```text
> cargo build

error[E0599]: no method named `unwrap` found for type `std::result::Result<std::cell::RefCell<fourth::Node<T>>, std::rc::Rc<std::cell::RefCell<fourth::Node<T>>>>` in the current scope
  --> src/fourth.rs:64:38
   |
64 |             Rc::try_unwrap(old_head).unwrap().into_inner().elem
   |                                      ^^^^^^
   |
   = note: the method `unwrap` exists but the following trait bounds were not satisfied:
           `std::rc::Rc<std::cell::RefCell<fourth::Node<T>>> : std::fmt::Debug`
```

呃。Result 上的`unwrap`要求你能把错误的那一侧调试打印出来。
`RefCell<T>`只有在`T`实现了`Debug`时才实现`Debug`。而`Node`没有实现 Debug。

与其去实现它，我们不如绕过去，用`ok`把 Result 转成 Option：

```rust ,ignore
Rc::try_unwrap(old_head).ok().unwrap().into_inner().elem
```

求你了。

```text
cargo build

```

太好了。

*长舒一口气*

我们做到了。

我们实现了`push`和`pop`。

我们来偷用一下以前`stack`的基础测试来试试（因为到目前为止我们也就实现了这些）：

```rust ,ignore
#[cfg(test)]
mod test {
    use super::List;

    #[test]
    fn basics() {
        let mut list = List::new();

        // Check empty list behaves right
        assert_eq!(list.pop_front(), None);

        // Populate list
        list.push_front(1);
        list.push_front(2);
        list.push_front(3);

        // Check normal removal
        assert_eq!(list.pop_front(), Some(3));
        assert_eq!(list.pop_front(), Some(2));

        // Push some more just to make sure nothing's corrupted
        list.push_front(4);
        list.push_front(5);

        // Check normal removal
        assert_eq!(list.pop_front(), Some(5));
        assert_eq!(list.pop_front(), Some(4));

        // Check exhaustion
        assert_eq!(list.pop_front(), Some(1));
        assert_eq!(list.pop_front(), None);
    }
}
```

```text
cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 9 tests
test first::test::basics ... ok
test fourth::test::basics ... ok
test second::test::iter_mut ... ok
test second::test::basics ... ok
test fifth::test::iter_mut ... ok
test third::test::basics ... ok
test second::test::iter ... ok
test third::test::iter ... ok
test second::test::into_iter ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured

```

*搞定收工*。

既然我们能正确地从链表里移除东西了，就可以实现 Drop 了。
这一次，Drop 在概念上要更有意思一些。以前我们费劲为栈实现 Drop，只是为了避免
无界递归；而现在我们必须实现 Drop，才能让*任何*事情发生。

`Rc`处理不了环。如果存在环，所有东西都会让其他所有东西一直活着。
而双向链表，说白了，就是一长串小环组成的大链条！所以当我们丢弃链表时，
两端的节点的引用计数会减到 1……然后就什么都不会发生了。好吧，如果我们的链表
恰好只包含一个节点，那还行。但理想情况下，链表在包含多个元素时也该正常工作。
也许只有我这么想吧。

正如我们所见，移除元素有点痛苦。所以对我们来说最简单的做法，就是不停地`pop`
直到拿到 None：

```rust ,ignore
impl<T> Drop for List<T> {
    fn drop(&mut self) {
        while self.pop_front().is_some() {}
    }
}
```

```text
cargo build

```

（其实我们的可变栈也可以这么干，但捷径是留给真正懂行的人的！）

我们本可以看看怎么实现`push`和`pop`的`_back`版本，但那不过是复制粘贴的活儿，
我们把它推到本章后面再说。现在先来看点更有意思的东西！


[refcell]: https://doc.rust-lang.org/std/cell/struct.RefCell.html
[multirust]: https://github.com/brson/multirust
[downloads]: https://www.rust-lang.org/install.html
