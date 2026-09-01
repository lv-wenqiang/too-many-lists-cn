# IterMut

老实说，IterMut 简直是野的。这话本身听起来就挺野的；它不明摆着和 Iter
一模一样吗！

语义上确实如此，但共享引用和可变引用的本质决定了：Iter 是“平凡的”，
而 IterMut 则是货真价实的巫师魔法。

关键的洞见来自我们为 Iter 实现的 Iterator：

```rust ,ignore
impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> { /* stuff */ }
}
```

它可以去糖展开成：

```rust ,ignore
impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next<'b>(&'b mut self) -> Option<&'a T> { /* stuff */ }
}
```

`next`的签名在输入和输出的生命周期之间*没有*建立任何约束！
我们为什么要在意这个？因为这意味着我们可以无条件地一次又一次调用`next`！


```rust ,ignore
let mut list = List::new();
list.push(1); list.push(2); list.push(3);

let mut iter = list.iter();
let x = iter.next().unwrap();
let y = iter.next().unwrap();
let z = iter.next().unwrap();
```

酷！

对共享引用来说这*完全没问题*，因为共享引用的意义就在于你可以同时拥有一大堆。
然而可变引用*不能*共存。它们的意义恰恰在于独占。

最终的结果是，用安全代码写 IterMut 要困难得多（而我们甚至还没开始讲那到底
意味着什么……）。令人惊讶的是，IterMut 其实可以为许多结构完全安全地实现出来！

我们先把 Iter 的代码拿过来，把所有东西都改成可变的：

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

好吧，看起来我们这儿有两个不同的错误。不过第一个看着相当清楚，它甚至直接
告诉了我们该怎么修！你没法把共享引用升级成可变引用，所以`iter_mut`需要接受
`&mut self`。不过是个傻乎乎的复制粘贴错误。

```rust ,ignore
pub fn iter_mut(&mut self) -> IterMut<'_, T> {
    IterMut { next: self.head.as_deref_mut() }
}
```

那另一个呢？

哎呀！其实我在上一节写`iter`的实现时不小心犯了个错误，
而我们只是走运，它碰巧能用！

我们刚刚第一次撞上了 Copy 的魔法。在介绍[所有权][ownership]时我们说过，
当你移动了东西之后就不能再用它了。对某些类型来说，这完全说得通。
我们的好朋友 Box 替我们管理着堆上的一块分配，我们当然不希望有两段代码
都以为自己需要去释放它的内存。

但对另一些类型来说，这就是*扯淡*了。整数没有所有权语义；它们不过是些没有
意义的数字！这就是整数被标记为 Copy 的原因。Copy 类型是那些已知可以通过
按位拷贝完美复制的类型。因此它们有一项超能力：被移动之后，旧的值*仍然*可用。
其结果是，你甚至可以把一个 Copy 类型从引用中移出来，还不用做任何替换！

Rust 中所有的数值原始类型（i32、u64、bool、f32、char 等等）都是 Copy 的。
你也可以把任何自定义类型声明为 Copy，只要它的所有组成部分都是 Copy 的。

而这段代码之所以能跑通，关键在于：共享引用也是 Copy 的！因为`&`是 Copy 的，
所以`Option<&>`*也*是 Copy 的。于是我们写`self.next.map`时没出问题，
因为那个 Option 只是被拷贝了一份。现在我们不能这么干了，因为`&mut`不是 Copy 的
（如果你拷贝了一个 &mut，你就会有两个指向同一块内存位置的 &mut，这是被禁止的）。
取而代之，我们应该老老实实地`take`那个 Option 来把它拿到手。


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

呃……哇。我的天！IterMut 居然就这么好使了！

我们来测试一下：


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

没错。它能用。

我的天。

啥。

好吧，我是说它本来*就该*能用，只是通常总会有些蠢事横插一杠！
我们把话说清楚：

我们刚刚实现了这样一段代码：它接受一个单向链表，并且对链表中的每一个元素
最多返回一次可变引用。而且这一点是经过静态验证的。而且它完全安全。
而且我们没干任何出格的事。

要我说，这可是件大事。它之所以行得通，有这么几个原因：

* 我们`take`了那个`Option<&mut>`，因此我们独占地持有这个可变引用。
  不用担心还有谁会再去看它一眼。
* Rust 明白，把一个可变引用拆分到它所指向的结构体的各个子字段上是没问题的，
  因为没有办法“往回走”，而且这些子字段肯定是互不相交的。

事实证明，你也可以把这套基本逻辑套用到数组或者树上，得到一个安全的 IterMut！
你甚至可以把这个迭代器做成 DoubleEnded 的，这样你就能同时从前端*和*后端
消耗它了！哇哦！

[ownership]: first-ownership.md
