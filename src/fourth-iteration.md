# 迭代

我们来试试给这个大家伙做迭代。

## IntoIter

IntoIter 一如既往是最容易的。把栈包起来然后调用`pop`就行了：

```rust ,ignore
pub struct IntoIter<T>(List<T>);

impl<T> List<T> {
    pub fn into_iter(self) -> IntoIter<T> {
        IntoIter(self)
    }
}

impl<T> Iterator for IntoIter<T> {
    type Item = T;
    fn next(&mut self) -> Option<Self::Item> {
        self.0.pop_front()
    }
}
```

不过这次出现了一个有意思的新情况。以前我们的链表只有一种“自然的”迭代顺序，
而双端队列天生就是双向的。从前往后有什么特别的吗？如果有人想朝另一个方向
迭代呢？

Rust 其实对此有个答案：`DoubleEndedIterator`。DoubleEndedIterator
*继承*自 Iterator（意思是所有 DoubleEndedIterator 都是迭代器），
并要求一个新方法：`next_back`。它的签名和`next`完全一样，
但它应该从另一端产出元素。DoubleEndedIterator 的语义对我们来说超级方便：
这个迭代器变成了一个双端队列。你可以从前端和后端消耗元素，
直到两端相遇，此时迭代器就空了。

就像 Iterator 和`next`一样，事实证明 DoubleEndedIterator 的使用者其实并不怎么
关心`next_back`本身。这个接口最棒的地方在于，它暴露了`rev`方法，
该方法会把迭代器包起来，造出一个按相反顺序产出元素的新迭代器。
它的语义相当直白：在反转后的迭代器上调用`next`，其实就是调用`next_back`。

总之，因为我们本来就是个双端队列，提供这个 API 相当容易：

```rust ,ignore
impl<T> DoubleEndedIterator for IntoIter<T> {
    fn next_back(&mut self) -> Option<T> {
        self.0.pop_back()
    }
}
```

来测试一下：

```rust ,ignore
#[test]
fn into_iter() {
    let mut list = List::new();
    list.push_front(1); list.push_front(2); list.push_front(3);

    let mut iter = list.into_iter();
    assert_eq!(iter.next(), Some(3));
    assert_eq!(iter.next_back(), Some(1));
    assert_eq!(iter.next(), Some(2));
    assert_eq!(iter.next_back(), None);
    assert_eq!(iter.next(), None);
}
```


```text
cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 11 tests
test fourth::test::basics ... ok
test fourth::test::peek ... ok
test fourth::test::into_iter ... ok
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::iter ... ok
test second::test::iter_mut ... ok
test third::test::iter ... ok
test third::test::basics ... ok
test second::test::into_iter ... ok
test second::test::peek ... ok

test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured

```

不错。

## Iter

Iter 就没那么好说话了。我们又得跟那些讨厌的`Ref`打交道！因为有 Ref 在，
我们没法像以前那样存`&Node`。那我们就试着存`Ref<Node>`吧：

```rust ,ignore
pub struct Iter<'a, T>(Option<Ref<'a, Node<T>>>);

impl<T> List<T> {
    pub fn iter(&self) -> Iter<T> {
        Iter(self.head.as_ref().map(|head| head.borrow()))
    }
}
```

```text
> cargo build

```

到目前为止都还行。实现`next`会有点棘手，不过我觉得它的基本逻辑跟以前栈的
IterMut 是一样的，只是多了一层 RefCell 带来的疯狂：

```rust ,ignore
impl<'a, T> Iterator for Iter<'a, T> {
    type Item = Ref<'a, T>;
    fn next(&mut self) -> Option<Self::Item> {
        self.0.take().map(|node_ref| {
            self.0 = node_ref.next.as_ref().map(|head| head.borrow());
            Ref::map(node_ref, |node| &node.elem)
        })
    }
}
```

```text
cargo build

error[E0521]: borrowed data escapes outside of closure
   --> src/fourth.rs:155:13
    |
153 |     fn next(&mut self) -> Option<Self::Item> {
    |             --------- `self` is declared here, outside of the closure body
154 |         self.0.take().map(|node_ref| {
155 |             self.0 = node_ref.next.as_ref().map(|head| head.borrow());
    |             ^^^^^^   -------- borrow is only valid in the closure body
    |             |
    |             reference to `node_ref` escapes the closure body here

error[E0505]: cannot move out of `node_ref` because it is borrowed
   --> src/fourth.rs:156:22
    |
153 |     fn next(&mut self) -> Option<Self::Item> {
    |             --------- lifetime `'1` appears in the type of `self`
154 |         self.0.take().map(|node_ref| {
155 |             self.0 = node_ref.next.as_ref().map(|head| head.borrow());
    |             ------   -------- borrow of `node_ref` occurs here
    |             |
    |             assignment requires that `node_ref` is borrowed for `'1`
156 |             Ref::map(node_ref, |node| &node.elem)
    |                      ^^^^^^^^ move out of `node_ref` occurs here
```

糟糕。

`node_ref`活得不够久。与普通引用不同，Rust 不允许我们就那样把 Ref 拆开。
我们从`head.borrow()`拿到的那个 Ref 只被允许活得和`node_ref`一样久，
可我们在`Ref::map`调用里把它给毁掉了。

我们想要的那个函数是存在的，它叫做*[map_split][]*：

```rust ,ignore
pub fn map_split<U, V, F>(orig: Ref<'b, T>, f: F) -> (Ref<'b, U>, Ref<'b, V>) where
    F: FnOnce(&T) -> (&U, &V),
    U: ?Sized,
    V: ?Sized,
```

汪。来试试看……

```rust ,ignore
fn next(&mut self) -> Option<Self::Item> {
    self.0.take().map(|node_ref| {
        let (next, elem) = Ref::map_split(node_ref, |node| {
            (&node.next, &node.elem)
        });

        self.0 = next.as_ref().map(|head| head.borrow());

        elem
    })
}
```

```text
cargo build
   Compiling lists v0.1.0 (/Users/ADesires/dev/temp/lists)
error[E0521]: borrowed data escapes outside of closure
   --> src/fourth.rs:159:13
    |
153 |     fn next(&mut self) -> Option<Self::Item> {
    |             --------- `self` is declared here, outside of the closure body
...
159 |             self.0 = next.as_ref().map(|head| head.borrow());
    |             ^^^^^^   ---- borrow is only valid in the closure body
    |             |
    |             reference to `next` escapes the closure body here
```

呃。我们得再用一次`Ref::Map`才能让生命周期对上。但`Ref::Map`返回的是一个`Ref`，
而我们需要的是`Option<Ref>`，可我们又必须穿过 Ref 才能在 Option 上做 map……

**长时间凝视远方**

??????

```rust ,ignore
fn next(&mut self) -> Option<Self::Item> {
    self.0.take().map(|node_ref| {
        let (next, elem) = Ref::map_split(node_ref, |node| {
            (&node.next, &node.elem)
        });

        self.0 = if next.is_some() {
            Some(Ref::map(next, |next| &**next.as_ref().unwrap()))
        } else {
            None
        };

        elem
    })
}
```

```text
error[E0308]: mismatched types
   --> src/fourth.rs:162:22
    |
162 |                 Some(Ref::map(next, |next| &**next.as_ref().unwrap()))
    |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ expected struct `fourth::Node`, found struct `std::cell::RefCell`
    |
    = note: expected type `std::cell::Ref<'_, fourth::Node<_>>`
               found type `std::cell::Ref<'_, std::cell::RefCell<fourth::Node<_>>>`
```

哦。对哦。有好多个 RefCell。我们在链表里走得越深，就在每一个 RefCell 底下
嵌套得越深。我们大概得维护一个 Ref 的栈，来表示我们手上所有未归还的借用，
因为一旦我们不再看某个元素，就得把它前面每一个 RefCell 的借用计数都减掉
.................

我觉得这里我们已经无计可施了。这是条死路。我们试着从 RefCell 里跳出来吧。

那我们的`Rc`呢。谁说我们非得存引用不可？为什么不能直接把整个 Rc 克隆一份，
得到一个指向链表中间、漂亮的、拥有所有权的句柄呢？

```rust ,ignore
pub struct Iter<T>(Option<Rc<Node<T>>>);

impl<T> List<T> {
    pub fn iter(&self) -> Iter<T> {
        Iter(self.head.as_ref().map(|head| head.clone()))
    }
}

impl<T> Iterator for Iter<T> {
    type Item =
```

呃……等等，我们现在返回什么？`&T`？`Ref<T>`？

不行，这些都不行……我们的 Iter 已经没有生命周期了！`&T`和`Ref<T>`都要求我们
在进入`next`之前就先声明某个生命周期。可我们从 Rc 里弄出来的任何东西
都会是在借用这个迭代器……脑子……疼……啊啊啊啊啊啊

也许我们可以……对 Rc……做 map……来得到一个`Rc<T>`？有这种东西吗？
Rc 的文档里似乎没有类似的玩意儿。实际上有人做了[一个 crate][own-ref]，
让你能干这件事。

但等一下，就算我们*那么*干了，我们还有一个更大的问题：迭代器失效这个可怕的
幽灵。以前我们对迭代器失效是完全免疫的，因为 Iter 借用了链表，让它彻底不可变。
然而如果我们的 Iter 产出的是 Rc，它们就压根不借用链表了！这意味着人们可以在
手里攥着指向链表内部的指针时，对链表调用`push`和`pop`！

老天爷，那会造成什么后果？！

嗯，压入其实没问题。我们持有的是链表某个子区间的视图，链表只会在我们的视野
之外长大而已。没什么大不了的。

但`pop`就是另一回事了。如果他们弹出的是我们区间之外的元素，那*仍然*没问题。
我们看不见那些节点，所以什么都不会发生。可要是他们试图把我们正指着的那个节点
弹出去……一切都会爆炸！具体来说，当他们去`unwrap`那个`try_unwrap`的结果时，
它会真的失败，整个程序就会 panic。

这其实挺酷的。我们可以拿到一大堆指向链表内部、拥有所有权的指针，
同时还能修改链表，*而且它就是能用*，直到他们试图移除我们正指着的节点为止。
就算到了那一步，我们也不会得到悬垂指针之类的东西，程序会确定性地 panic！

但在对 Rc 做 map 之上还得处理迭代器失效，这看起来就……很糟。`Rc<RefCell>`
这次是真的、彻底地辜负我们了。有意思的是，我们经历的正好是持久化栈那一幕的
反面。持久化栈很难重新夺回数据的所有权，却可以随时随地拿到引用；
而我们这个链表获得所有权毫无压力，却在把引用借出去这件事上举步维艰。

不过平心而论，我们大部分的挣扎都围绕着想要隐藏实现细节、给出一个体面的 API。
如果我们愿意到处传来传去 Node，那一切*都能*搞定。

见鬼，我们甚至可以造出多个并发的 IterMut，并在运行时检查它们没有同时可变地
访问同一个元素！

说真的，这种设计更适合那种永远不会暴露给 API 使用者的内部数据结构。
内部可变性非常适合用来写安全的*应用程序*。用来写安全的*库*就没那么合适了。

总之，Iter 和 IterMut 我就放弃了。我们本来能做出来，但*呃*。

[own-ref]: https://crates.io/crates/owning_ref
[map-split]: https://doc.rust-lang.org/std/cell/struct.Ref.html#method.map_split
