# Send、Sync 与编译测试

好吧，其实我们还有一对特征要考虑，不过它们很特殊。我们得对付 Rust 的神圣罗马帝国：不安全的选择加入内建特征（OIBIT）：[Send 和 Sync](https://doc.rust-lang.org/nomicon/send-and-sync.html)——而它们实际上是选择退出、而且是外建的（三个词里对了一个，相当不错了！）。

和 Copy 一样，这两个特征完全没有与之关联的代码，只是用来标记你的类型具备某项性质。Send 表示你的类型可以安全地发送到另一个线程。Sync 表示你的类型可以安全地在线程之间共享（&Self: Send）。

关于 LinkedList 为什么协变的那套论证在这里同样适用：一般来说，那些不使用花哨内部可变性技巧的普通集合，让它们 Send 和 Sync 都是安全的。

但我说过它们是*选择退出*的。那么实际上，我们是不是已经是了？我们怎么知道呢？

我们往代码里加点新魔法：一些随机的私有垃圾代码，只有当我们的类型具备我们期望的性质时它才能编译通过：

```rust ,ignore
#[allow(dead_code)]
fn assert_properties() {
    fn is_send<T: Send>() {}
    fn is_sync<T: Sync>() {}

    is_send::<LinkedList<i32>>();
    is_sync::<LinkedList<i32>>();

    is_send::<IntoIter<i32>>();
    is_sync::<IntoIter<i32>>();

    is_send::<Iter<i32>>();
    is_sync::<Iter<i32>>();

    is_send::<IterMut<i32>>();
    is_sync::<IterMut<i32>>();

    is_send::<Cursor<i32>>();
    is_sync::<Cursor<i32>>();

    fn linked_list_covariant<'a, T>(x: LinkedList<&'static T>) -> LinkedList<&'a T> { x }
    fn iter_covariant<'i, 'a, T>(x: Iter<'i, &'static T>) -> Iter<'i, &'a T> { x }
    fn into_iter_covariant<'a, T>(x: IntoIter<&'static T>) -> IntoIter<&'a T> { x }
}
```

```text
cargo build
   Compiling linked-list v0.0.3 
error[E0277]: `NonNull<Node<i32>>` cannot be sent between threads safely
   --> src\lib.rs:433:5
    |
433 |     is_send::<LinkedList<i32>>();
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^ `NonNull<Node<i32>>` cannot be sent between threads safely
    |
    = help: within `LinkedList<i32>`, the trait `Send` is not implemented for `NonNull<Node<i32>>`
    = note: required because it appears within the type `Option<NonNull<Node<i32>>>`
note: required because it appears within the type `LinkedList<i32>`
   --> src\lib.rs:8:12
    |
8   | pub struct LinkedList<T> {
    |            ^^^^^^^^^^
note: required by a bound in `is_send`
   --> src\lib.rs:430:19
    |
430 |     fn is_send<T: Send>() {}
    |                   ^^^^ required by this bound in `is_send`

<a million more errors>
```

哎哟，怎么回事！我那个神圣罗马帝国的好梗都准备好了！

嗯，我说原始指针只有一项安全防护时骗了你：这就是另一项。`*const`和`*mut`为了安全都显式地选择退出了 Send 和 Sync，所以我们*确实*得把它们重新选回来：

```rust ,ignore
unsafe impl<T: Send> Send for LinkedList<T> {}
unsafe impl<T: Sync> Sync for LinkedList<T> {}

unsafe impl<'a, T: Send> Send for Iter<'a, T> {}
unsafe impl<'a, T: Sync> Sync for Iter<'a, T> {}

unsafe impl<'a, T: Send> Send for IterMut<'a, T> {}
unsafe impl<'a, T: Sync> Sync for IterMut<'a, T> {}
```

注意我们在这里必须写*unsafe impl*：它们是*不安全特征*！不安全代码（比如并发库）可以依赖我们正确地实现这些特征！既然这里没有实际代码，我们所做的保证就仅仅是：是的，我们确实可以安全地在线程之间发送或共享！

别轻率地把这些往上一拍，不过我作为一名持证专业人士在此声明：没错，这些完全没问题。注意我们不需要为 IntoIter 实现 Send 和 Sync：它只包含一个 LinkedList，所以会自动推导出 Send 和 Sync &mdash; 我就说它们其实是选择退出的吧！（退出的语法很滑稽，是`impl !Send for MyType {}`。）

```text
cargo build
   Compiling linked-list v0.0.3
    Finished dev [unoptimized + debuginfo] target(s) in 0.18s
```

好，不错！

……等等，其实如果那些*不该*具备这些性质的东西却具备了，那才真的危险。特别是 IterMut，它*绝对*不该是协变的，因为它“像”`&mut T`。可我们要怎么检查这一点呢？

用魔法！好吧，其实是用 rustdoc！好吧我们也不是非得用 rustdoc 干这事，但这是最有意思的做法。你看，如果你写一段文档注释并在里面放一个代码块，rustdoc 就会尝试编译并运行它，所以我们可以用它来造出全新的匿名“程序”，而不影响主程序：


```rust ,ignore
    /// ```
    /// use linked_list::IterMut;
    /// 
    /// fn iter_mut_covariant<'i, 'a, T>(x: IterMut<'i, &'static T>) -> IterMut<'i, &'a T> { x }
    /// ```
    fn iter_mut_invariant() {}
```

```text
cargo test

...

   Doc-tests linked-list

running 1 test
test src\lib.rs - assert_properties::iter_mut_invariant (line 458) ... FAILED

failures:

---- src\lib.rs - assert_properties::iter_mut_invariant (line 458) stdout ----
error[E0308]: mismatched types
 --> src\lib.rs:461:86
  |
6 | fn iter_mut_covariant<'i, 'a, T>(x: IterMut<'i, &'static T>) -> IterMut<'i, &'a T> { x }
  |                                                                                      ^ lifetime mismatch
  |
  = note: expected struct `linked_list::IterMut<'_, &'a T>`
             found struct `linked_list::IterMut<'_, &'static T>`
```

好，酷，我们证明了它是不变的，可是呃，现在我们的测试失败了。别担心，rustdoc 让你可以给围栏加上 compile_fail 标注，说明这是预期之中的！

（其实我们只证明了它“不是协变的”，不过老实说，你要是真能搞出一个“意外且错误地逆变”的类型，那，恭喜？）

```rust ,ignore
    /// ```compile_fail
    /// use linked_list::IterMut;
    /// 
    /// fn iter_mut_covariant<'i, 'a, T>(x: IterMut<'i, &'static T>) -> IterMut<'i, &'a T> { x }
    /// ```
    fn iter_mut_invariant() {}
```

```text
cargo test
   Compiling linked-list v0.0.3
    Finished test [unoptimized + debuginfo] target(s) in 0.49s
     Running unittests src\lib.rs

...

   Doc-tests linked-list

running 1 test
test src\lib.rs - assert_properties::iter_mut_invariant (line 458) - compile fail ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.12s
```

好耶！我建议总是先写一个不带 compile_fail 的版本，这样你就能确认它是*因为正确的理由*而编译失败的。举个例子，如果你忘了写`use`，那个测试同样会失败（因而“通过”），而这可不是我们想要的！虽然从概念上讲，能够“要求”编译器给出某个特定错误听着挺诱人，可这会是一场彻头彻尾的噩梦，实际上等于让*编译器产出更好的错误信息*变成一次破坏性变更。我们希望编译器变得更好，所以，不行，你没这个待遇。

（哦等等，我们其实可以在 compile_fail 旁边指定想要的错误码，**但这只在 nightly 上有效，而且出于上面所说的理由，依赖它是个坏主意。在非 nightly 上它会被静默忽略。**）

```rust ,ignore
    /// ```compile_fail,E0308
    /// use linked_list::IterMut;
    /// 
    /// fn iter_mut_covariant<'i, 'a, T>(x: IterMut<'i, &'static T>) -> IterMut<'i, &'a T> { x }
    /// ```
    fn iter_mut_invariant() {}
```

……另外，你注意到我们其实已经把 IterMut 弄成不变的了吗？这很容易被漏掉，因为我“只是”复制粘贴了 Iter 然后丢在了最后。就是这儿的最后一行：

```rust ,ignore
pub struct IterMut<'a, T> {
    front: Link<T>,
    back: Link<T>,
    len: usize,
    _boo: PhantomData<&'a mut T>,
}
```

我们来试着把那个 PhantomData 去掉：

```text
 cargo build
   Compiling linked-list v0.0.3 (C:\Users\ninte\dev\contain\linked-list)
error[E0392]: parameter `'a` is never used
  --> src\lib.rs:30:20
   |
30 | pub struct IterMut<'a, T> {
   |                    ^^ unused parameter
   |
   = help: consider removing `'a`, referring to it in a field, or using a marker such as `PhantomData`
```

哈！编译器给我们兜着底，不会就这么让我们*不*使用那个生命周期。那我们改成用一个*错误的*示例试试：

```rust ,ignore
    _boo: PhantomData<&'a T>,
```

```text
cargo build
   Compiling linked-list v0.0.3 (C:\Users\ninte\dev\contain\linked-list)
    Finished dev [unoptimized + debuginfo] target(s) in 0.17s
```

它编译过了！那我们的测试现在能抓到问题吗？

```text
cargo test

...

   Doc-tests linked-list

running 1 test
test src\lib.rs - assert_properties::iter_mut_invariant (line 458) - compile fail ... FAILED

failures:

---- src\lib.rs - assert_properties::iter_mut_invariant (line 458) stdout ----
Test compiled successfully, but it's marked `compile_fail`.

failures:
    src\lib.rs - assert_properties::iter_mut_invariant (line 458)

test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.15s
```

耶！！！这套机制管用！我就喜欢有真正干活的测试，这样我就不必对那些若隐若现的错误那么惊恐了！

