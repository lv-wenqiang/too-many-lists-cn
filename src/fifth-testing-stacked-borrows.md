# 测试 Stacked Borrows（堆叠借用）

> 上一节那套（简化的）Rust 内存模型的太长不看版：
>
> * Rust 在概念上通过维护一个“借用栈”来处理重借用
> * 只有栈顶的那个是“活的”（拥有独占访问权）
> * 当你访问一个较低的借用时，它会变成“活的”，而它之上的那些会被弹出
> * 你不被允许使用已经从借用栈中弹出的指针
> * 借用检查器确保安全代码遵守这一点
> * 理论上 miri 会在运行时检查原始指针是否遵守这一点

上面都是大量的理论和想法——现在让我们进入本书真正的核心与灵魂：写点糟糕的代码，然后让工具冲我们尖叫。我们要过一*大堆*例子，看看我们的心智模型是否说得通，并试着培养出对堆叠借用的直觉。

> **旁白：**在实践中捕捉未定义行为是件棘手的事。毕竟你面对的是编译器字面意义上*假定*不会发生的情况。
>
> 如果你运气好，今天它们会“看起来能用”，但对于更聪明的编译器或者代码的细微改动来说，它们就是颗定时炸弹。如果你*非常*走运，事情会稳定地崩掉，这样你就能抓住错误并修好它。可要是你运气不好，东西就会以各种诡异而费解的方式坏掉。
>
> Miri 试图绕开这一点：它取用 rustc 对程序最朴素、最未经优化的视图，并在解释执行时追踪额外的状态。就“消毒器”这类工具而言，这是一种相当确定、相当稳健的做法，但它永远不会是*完美*的。你需要你的测试程序真的执行到那个未定义行为；而对一个足够大的程序来说，引入各种不确定性太容易了（HashMap 默认就用随机数！）。
>
> 我们永远不能把 miri 认可我们程序的执行当成“绝对没有未定义行为”的确凿断言。miri 也有可能*以为*某处是未定义行为，而实际上并不是。但如果我们心里有一套关于事情如何运作的模型，而 miri 似乎也同意我们，那就是个好兆头，说明我们走在正确的路上。




# 基本的借用

在前面几节里我们看到，借用检查器不喜欢这样的代码：

```rust ,ignore
let mut data = 10;
let ref1 = &mut data;
let ref2 = &mut *ref1;

// ORDER SWAPPED!
*ref1 += 1;
*ref2 += 2;

println!("{}", data);
```

我们来看看把`ref2`换成`*mut`会发生什么：

```rust ,ignore
unsafe {
    let mut data = 10;
    let ref1 = &mut data;
    let ptr2 = ref1 as *mut _;

    // ORDER SWAPPED!
    *ref1 += 1;
    *ptr2 += 2;

    println!("{}", data);
}
```

```text
cargo run
   Compiling miri-sandbox v0.1.0
    Finished dev [unoptimized + debuginfo] target(s) in 0.71s
     Running `target\debug\miri-sandbox.exe`
13
```

Rustc 看起来非常满意：没有警告，程序也产生了我们预期的结果！现在我们来看看 miri（在严格模式下）怎么看它：

```text
MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

    Finished dev [unoptimized + debuginfo] target(s) in 0.00s
     Running cargo-miri.exe target\miri

error: Undefined Behavior: no item granting read access 
to tag <untagged> at alloc748 found in borrow stack.

 --> src\main.rs:9:9
  |
9 |         *ptr2 += 2;
  |         ^^^^^^^^^^ no item granting read access to tag <untagged> 
  |                    at alloc748 found in borrow stack.
  |
  = help: this indicates a potential bug in the program: 
    it performed an invalid operation, but the rules it 
    violated are still experimental
 
```

漂亮！我们那套直觉模型站住脚了：虽然编译器没能替我们抓住问题，miri 抓住了。

我们来试点更复杂的，就是前面提到过的`&mut -> *mut -> &mut -> *mut`那种情况：

```rust ,ignore
unsafe {
    let mut data = 10;
    let ref1 = &mut data;
    let ptr2 = ref1 as *mut _;
    let ref3 = &mut *ptr2;
    let ptr4 = ref3 as *mut _;

    // Access the first raw pointer first
    *ptr2 += 2;

    // Then access things in "borrow stack" order
    *ptr4 += 4;
    *ref3 += 3;
    *ptr2 += 2;
    *ref1 += 1;

    println!("{}", data);
}
```

```text
cargo run
22

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

error: Undefined Behavior: no item granting read access 
to tag <1621> at alloc748 found in borrow stack.

  --> src\main.rs:13:5
   |
13 |     *ptr4 += 4;
   |     ^^^^^^^^^^ no item granting read access to tag <1621> 
   |                at alloc748 found in borrow stack.
   |
```

哇，果然！在严格模式下，miri 能“分辨”这两个原始指针，并让使用第二个指针使第一个失效。我们把那处把一切搞砸的第一次使用去掉，看看是不是就都正常了：

```rust ,ignore
unsafe {
    let mut data = 10;
    let ref1 = &mut data;
    let ptr2 = ref1 as *mut _;
    let ref3 = &mut *ptr2;
    let ptr4 = ref3 as *mut _;

    // Access things in "borrow stack" order
    *ptr4 += 4;
    *ref3 += 3;
    *ptr2 += 2;
    *ref1 += 1;

    println!("{}", data);
}
```

```text
cargo run
20

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
20
```

漂亮。

是啊，我觉得到这个份上我们都能去拿编程语言内存模型设计与实现的博士学位了。谁还*需要*编译器啊，这玩意儿*太简单*了。

> **旁白：**并不简单，不过我还是为你感到骄傲。





# 测试数组

我们来折腾一下数组和指针偏移（`add`和`sub`）。这应该没问题吧？

```rust ,ignore
unsafe {
    let mut data = [0; 10];
    let ref1_at_0 = &mut data[0];           // Reference to 0th element
    let ptr2_at_0 = ref1_at_0 as *mut i32;  // Ptr to 0th element
    let ptr3_at_1 = ptr2_at_0.add(1);       // Ptr to 1st element

    *ptr3_at_1 += 3;
    *ptr2_at_0 += 2;
    *ref1_at_0 += 1;

    // Should be [3, 3, 0, ...]
    println!("{:?}", &data[..]);
}
```

```text
cargo run
[3, 3, 0, 0, 0, 0, 0, 0, 0, 0]

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

error: Undefined Behavior: no item granting read access 
to tag <1619> at alloc748+0x4 found in borrow stack.
 --> src\main.rs:8:5
  |
8 |     *ptr3_at_1 += 3;
  |     ^^^^^^^^^^^^^^^ no item granting read access to tag <1619>
  |                     at alloc748+0x4 found in borrow stack.
```

*把研究生申请书撕了*

发生了什么？我们把借用栈用得好好的呀！难道`ptr -> ptr`会有什么奇怪的事情？如果我们只是复制指针，让它们都指向同一个位置呢：

```rust
unsafe {
    let mut data = [0; 10];
    let ref1_at_0 = &mut data[0];           // Reference to 0th element
    let ptr2_at_0 = ref1_at_0 as *mut i32;  // Ptr to 0th element
    let ptr3_at_0 = ptr2_at_0;              // Ptr to 0th element

    *ptr3_at_0 += 3;
    *ptr2_at_0 += 2;
    *ref1_at_0 += 1;

    // Should be [6, 0, 0, ...]
    println!("{:?}", &data[..]);
}
```

```text
cargo run
[6, 0, 0, 0, 0, 0, 0, 0, 0, 0]

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
[6, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

不对，这样是没问题的。也许我们只是运气好，那就把指针搞得一团糟试试：

```rust
unsafe {
    let mut data = [0; 10];
    let ref1_at_0 = &mut data[0];            // Reference to 0th element
    let ptr2_at_0 = ref1_at_0 as *mut i32;   // Ptr to 0th element
    let ptr3_at_0 = ptr2_at_0;               // Ptr to 0th element
    let ptr4_at_0 = ptr2_at_0.add(0);        // Ptr to 0th element
    let ptr5_at_0 = ptr3_at_0.add(1).sub(1); // Ptr to 0th element

    // An absolute jumbled hash of ptr usages
    *ptr3_at_0 += 3;
    *ptr2_at_0 += 2;
    *ptr4_at_0 += 4;
    *ptr5_at_0 += 5;
    *ptr3_at_0 += 3;
    *ptr2_at_0 += 2;
    *ref1_at_0 += 1;

    // Should be [20, 0, 0, ...]
    println!("{:?}", &data[..]);
}
```


```text
cargo run
[20, 0, 0, 0, 0, 0, 0, 0, 0, 0]

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
[20, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

还是没问题！事实上，对于那些从其他原始指针派生出来的原始指针，miri 要宽松得*多*。它们全都共享同一个“借用”（miri 管它叫*标签*）。

一旦你开始使用原始指针，它们就可以自由地分裂成各自的小小愤怒男，互相折腾。这没关系，因为编译器明白这一点，不会像对待引用那样去优化这些读写。

> **旁白：**如果代码足够简单，编译器仍然可以追踪所有派生出来的指针，并在可能的地方进行优化，只是这会比它对引用所能做的推理脆弱得多。

那*真正*的问题出在哪儿？

尽管`data`是一次“分配”（一个局部变量），`ref1_at_0`借用的却只是第一个元素。Rust 允许把借用拆开，让它们只作用于分配的特定部分！我们来试试：

```rust ,ignore
unsafe {
    let mut data = [0; 10];
    let ref1_at_0 = &mut data[0];           // Reference to 0th element
    let ref2_at_1 = &mut data[1];           // Reference to 1th element
    let ptr3_at_0 = ref1_at_0 as *mut i32;  // Ptr to 0th element
    let ptr4_at_1 = ref2_at_1 as *mut i32;   // Ptr to 1th element

    *ptr4_at_1 += 4;
    *ptr3_at_0 += 3;
    *ref2_at_1 += 2;
    *ref1_at_0 += 1;

    // Should be [3, 3, 0, ...]
    println!("{:?}", &data[..]);
}
```

```text
error[E0499]: cannot borrow `data[_]` as mutable more than once at a time
 --> src\main.rs:5:21
  |
4 |     let ref1_at_0 = &mut data[0];           // Reference to 0th element
  |                     ------------ first mutable borrow occurs here
5 |     let ref2_at_1 = &mut data[1];           // Reference to 1th element
  |                     ^^^^^^^^^^^^ second mutable borrow occurs here
6 |     let ptr3_at_0 = ref1_at_0 as *mut i32;  // Ptr to 0th element
  |                     --------- first borrow later used here
  |
  = help: consider using `.split_at_mut(position)` or similar method 
    to obtain two mutable non-overlapping sub-slices
```

糟糕！Rust 并不会追踪数组下标来证明这些借用互不相交，不过它确实给了我们`split_at_mut`，让我们能以一种可以放心假定其有效的方式，把一个切片拆成多个部分：

```rust
unsafe {
    let mut data = [0; 10];

    let slice1 = &mut data[..];
    let (slice2_at_0, slice3_at_1) = slice1.split_at_mut(1); 
    
    let ref4_at_0 = &mut slice2_at_0[0];    // Reference to 0th element
    let ref5_at_1 = &mut slice3_at_1[0];    // Reference to 1th element
    let ptr6_at_0 = ref4_at_0 as *mut i32;  // Ptr to 0th element
    let ptr7_at_1 = ref5_at_1 as *mut i32;  // Ptr to 1th element

    *ptr7_at_1 += 7;
    *ptr6_at_0 += 6;
    *ref5_at_1 += 5;
    *ref4_at_0 += 4;

    // Should be [10, 12, 0, ...]
    println!("{:?}", &data[..]);
}
```

```text
cargo run
[10, 12, 0, 0, 0, 0, 0, 0, 0, 0]

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
[10, 12, 0, 0, 0, 0, 0, 0, 0, 0]
```

嘿，这就行了！切片会明确地告诉编译器和 miri“嘿，我把我这个范围内的所有内存都借走了”，于是它们就知道其中所有元素都可以被修改。

另外要注意，`split_at_mut`这类操作被允许，说明借用与其说是一个*栈*，不如说更像一棵*树*，因为我们可以把一个大的借用拆成一堆互不相交的小借用，而一切照样能用。

（我觉得在真正的堆叠借用模型里，一切仍然是栈，因为这些栈在概念上追踪的是程序中每个字节的权限……吧？）

要是我们*直接*把一个切片转成指针呢？那个指针会拥有对整个切片的访问权吗？

```rust
unsafe {
    let mut data = [0; 10];

    let slice1_all = &mut data[..];         // Slice for the entire array
    let ptr2_all = slice1_all.as_mut_ptr(); // Pointer for the entire array
    
    let ptr3_at_0 = ptr2_all;               // Pointer to 0th elem (the same)
    let ptr4_at_1 = ptr2_all.add(1);        // Pointer to 1th elem
    let ref5_at_0 = &mut *ptr3_at_0;        // Reference to 0th elem
    let ref6_at_1 = &mut *ptr4_at_1;        // Reference to 1th elem

    *ref6_at_1 += 6;
    *ref5_at_0 += 5;
    *ptr4_at_1 += 4;
    *ptr3_at_0 += 3;

    // Just for fun, modify all the elements in a loop
    // (Could use any of the raw pointers for this, they share a borrow!)
    for idx in 0..10 {
        *ptr2_all.add(idx) += idx;
    }

    // Safe version of this same code for fun
    for (idx, elem_ref) in slice1_all.iter_mut().enumerate() {
        *elem_ref += idx; 
    }

    // Should be [8, 12, 4, 6, 8, 10, 12, 14, 16, 18]
    println!("{:?}", &data[..]);
}
```


```text
cargo run
[8, 12, 4, 6, 8, 10, 12, 14, 16, 18]

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
[8, 12, 4, 6, 8, 10, 12, 14, 16, 18]
```


漂亮！指针不只是整数：它们身上关联着一段内存范围，而在 Rust 里我们还可以把这个范围收窄！





# 测试共享引用

在前面所有这些例子里，我都非常小心地只使用可变引用，并做读-改-写操作（`+=`），好让事情尽可能简单。

但 Rust 还有共享引用，它们是只读的，而且可以被自由复制，这些又该怎么算呢？嗯，我们已经看到原始指针可以被自由复制，而我们处理它的办法是说它们“共享”同一个借用。也许我们可以同样看待共享引用？

我们用一个读取值的函数来测试一下（`println!`在自动取引用／解引用方面有点玄，所以我把它包进一个函数里，以确保我们测的确实是想测的东西）：

```rust ,ignore
fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = 10;
    let mref1 = &mut data;
    let sref2 = &mref1;
    let sref3 = sref2;
    let sref4 = &*sref2;

    // Random hash of shared reference reads
    opaque_read(sref3);
    opaque_read(sref2);
    opaque_read(sref4);
    opaque_read(sref2);
    opaque_read(sref3);

    *mref1 += 1;

    opaque_read(&data);
}
```

```text
cargo run

warning: unnecessary `unsafe` block
 --> src\main.rs:6:1
  |
6 | unsafe {
  | ^^^^^^ unnecessary `unsafe` block
  |
  = note: `#[warn(unused_unsafe)]` on by default

warning: `miri-sandbox` (bin "miri-sandbox") generated 1 warning

10
10
10
10
10
11
```

哦对，我们忘了对原始指针做点什么，不过至少我们能看到，所有共享引用可以互换着用，完全没问题。现在我们来掺进一些原始指针：

```rust ,ignore
fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = 10;
    let mref1 = &mut data;
    let ptr2 = mref1 as *mut i32;
    let sref3 = &mref1;
    let ptr4 = sref3 as *mut i32;

    *ptr4 += 4;
    opaque_read(sref3);
    *ptr2 += 2;
    *mref1 += 1;

    opaque_read(&data);
}
```

```text
cargo run

error[E0606]: casting `&&mut i32` as `*mut i32` is invalid
  --> src\main.rs:11:16
   |
11 |     let ptr4 = sref3 as *mut i32;
   |                ^^^^^^^^^^^^^^^^^
```

哎呀，我们其实一直在摆弄的是`& &mut`而不是`&`！Rust 非常擅长在这无关紧要时替你把它糊过去。我们用`let sref3 = &*mref1`来正经地重借用一下：


```text
cargo run

error[E0606]: casting `&i32` as `*mut i32` is invalid
  --> src\main.rs:11:16
   |
11 |     let ptr4 = sref3 as *mut i32;
   |                ^^^^^^^^^^^^^^^^^
```

不行，Rust 还是不喜欢！你只能把共享引用转换成`*const`，而它只能读。可要是我们就……这么……干呢……？

```rust ,ignore
    let ptr4 = sref3 as *const i32 as *mut i32;
```

```text
cargo run

14
17
```

什么。行吧，随便？Rust 这转换系统真棒。这简直就像是在说`*const`是个相当没用的类型，存在的意义不过是描述 C 的 API，以及隐约暗示一下正确用法（它确实是，也确实在这么干）。miri 怎么看？

```text
MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

error: Undefined Behavior: no item granting write access to 
tag <1621> at alloc742 found in borrow stack.
  --> src\main.rs:13:5
   |
13 |     *ptr4 += 4;
   |     ^^^^^^^^^^ no item granting write access to tag <1621>
   |                at alloc742 found in borrow stack.
```

唉，尽管我们可以用两次转换来绕开编译器的抱怨，但这并不会让这个操作真的*被允许*。当我们取得共享引用时，我们就承诺了不去修改这个值。

这一点很重要，因为它意味着当那个共享借用从借用栈上被弹出时，它下面的可变指针*可以*假定内存没有被改动过。期间也许有一些小小愤怒男在*读*这块内存（所以写入必须真正提交），但他们没法修改它，于是那些可变指针可以假定自己最后写进去的值还在那儿！

**一旦共享引用进入借用栈，压在它上面的一切就都只有读权限。**

不过我们可以这么做：

```rust
fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = 10;
    let mref1 = &mut data;
    let ptr2 = mref1 as *mut i32;
    let sref3 = &*mref1;
    let ptr4 = sref3 as *const i32 as *mut i32;

    opaque_read(&*ptr4);
    opaque_read(sref3);
    *ptr2 += 2;
    *mref1 += 1;

    opaque_read(&data);
}
```

注意，只要我们实际上只从中读取，创建一个可变的原始指针仍然是“没问题”的！

```text
cargo run
10
10
13

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
10
10
13
```

另外，为了保险起见，我们来检查一下共享引用是不是也会像平常那样被弹出：

```rust ,ignore
fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = 10;
    let mref1 = &mut data;
    let ptr2 = mref1 as *mut i32;
    let sref3 = &*mref1;

    *ptr2 += 2;
    opaque_read(sref3); // Read in the wrong order?
    *mref1 += 1;

    opaque_read(&data);
}
```

```text
cargo run
12
13

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

error: Undefined Behavior: trying to reborrow for SharedReadOnly 
at alloc742, but parent tag <1620> does not have an appropriate 
item in the borrow stack

  --> src\main.rs:13:17
   |
13 |     opaque_read(sref3); // Read in the wrong order?
   |                 ^^^^^ trying to reborrow for SharedReadOnly 
   |                       at alloc742, but parent tag <1620> 
   |                       does not have an appropriate item 
   |                       in the borrow stack
   |
```

嘿，我们甚至得到了一条略有不同的错误信息，说的是 SharedReadOnly 而不是某个具体的标签。这说得通：一旦出现了*任何*共享引用，其余东西基本上就成了一锅 SharedReadOnly 的大杂烩，没必要再区分它们了！





# 测试内部可变性

还记得书里那可怕的一章吗？我们试着用 RefCell 和 Rc 做链表，在写这该死的链表时一切都比平常更糟糕。

我们一直坚称共享引用不能用来修改，可那一章讲的恰恰是你如何能借助*内部可变性*透过共享引用进行修改。我们来试试那个既好用又简单的 [std::cell::Cell](https://doc.rust-lang.org/std/cell/struct.Cell.html) 类型：

```rust
use std::cell::Cell;

unsafe {
    let mut data = Cell::new(10);
    let mref1 = &mut data;
    let ptr2 = mref1 as *mut Cell<i32>;
    let sref3 = &*mref1;

    sref3.set(sref3.get() + 3);
    (*ptr2).set((*ptr2).get() + 2);
    mref1.set(mref1.get() + 1);

    println!("{}", data.get());
}
```

啊，多么美丽的一团糟。看着 miri 冲它啐一口一定很愉快。


```text
cargo run
16

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
16
```

等等，真的假的？*这样*居然没问题？为什么？怎么会？*Cell*到底是个什么东西？

*砸开标准库上的挂锁*

```rust ,ignore
pub struct Cell<T: ?Sized> {
    value: UnsafeCell<T>,
}
```

`UnsafeCell`又是个什么鬼？

*再砸开一把挂锁，好让标准库知道我们是认真的*

```rust ,ignore
#[lang = "unsafe_cell"]
#[repr(transparent)]
#[repr(no_niche)]
pub struct UnsafeCell<T: ?Sized> {
    value: T,
}
```

哦，原来是巫师魔法。行吧。我猜。`#[lang = "unsafe_cell"]`说的字面意思就是 UnsafeCell 就是 UnsafeCell。别再砸锁了，我们去看看 [std::cell::UnsafeCell](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html) 的实际文档吧。

> Rust 中内部可变性的核心原语。
>
> 如果你有一个引用`&T`，那么在 Rust 里编译器通常会基于“`&T`指向不可变数据”这一认知来做优化。修改那份数据——比如通过一个别名，或者把`&T`transmute 成`&mut T`——被视为未定义行为。`UnsafeCell<T>`则放弃了对`&T`的不可变性保证：一个共享引用`&UnsafeCell<T>`可以指向正在被修改的数据。这就叫做“内部可变性”。

哦，它*真的*就是巫师魔法。

UnsafeCell 基本上是在告诉编译器“嘿听着，我们要拿这块内存搞点花样，别对它做那些通常的别名假设”。就像立起一块大牌子写着“注意：小小愤怒男出没”。

我们来看看加上 UnsafeCell 之后 miri 是不是就高兴了：

```rust ,ignore
use std::cell::UnsafeCell;

fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = UnsafeCell::new(10);
    let mref1 = data.get_mut();      // Get a mutable ref to the contents
    let ptr2 = mref1 as *mut i32;
    let sref3 = &*ptr2;

    *ptr2 += 2;
    opaque_read(sref3);
    *mref1 += 1;

    println!("{}", *data.get());
}
```

```text
cargo run
12
13

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

error: Undefined Behavior: trying to reborrow for SharedReadOnly
at alloc748, but parent tag <1629> does not have an appropriate
item in the borrow stack

  --> src\main.rs:15:17
   |
15 |     opaque_read(sref3);
   |                 ^^^^^ trying to reborrow for SharedReadOnly 
   |                       at alloc748, but parent tag <1629> does
   |                       not have an appropriate item in the
   |                       borrow stack
   |

```

等等，什么？我们明明念了咒语的！那我这一堆经联邦批准的、增强仪式效果的山羊血该怎么办？

嗯，我们是念了，可紧接着我们又用`get_mut`把这道咒语彻底作废了——它探进 UnsafeCell 内部，照样造出了一个正经的`&mut i32`！

想想看：如果编译器必须假定`&mut i32`*可能*正窥视着某个`UnsafeCell`的内部，那它就永远没法做出任何别名假设了！所有东西都可能塞满了小小愤怒男。

所以我们需要做的，是让`UnsafeCell`留在我们的指针类型里，好让编译器明白我们在干什么。

```rust
use std::cell::UnsafeCell;

fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = UnsafeCell::new(10);
    let mref1 = &mut data;              // Mutable ref to the *outside*
    let ptr2 = mref1.get();             // Get a raw pointer to the insides
    let sref3 = &*mref1;                // Get a shared ref to the *outside*

    *ptr2 += 2;                         // Mutate with the raw pointer
    opaque_read(&*sref3.get());         // Read from the shared ref
    *sref3.get() += 3;                  // Write through the shared ref
    *mref1.get() += 1;                  // Mutate with the mutable ref

    println!("{}", *data.get());
}
```


```text
cargo run
12
16

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
12
16
```

成了！看来这些血我到底还是不用倒掉。

其实，嘿，等一下。我们这里的顺序还是有点滑稽。我们先造了 ptr2，然后又从那个可变指针造出了 sref3。接着我们又在使用共享指针之前先用了原始指针。这一切看起来都……不太对。

其实等等，Cell 那个例子我们也是这么干的。嗯——。

我们只能得出两个结论之一：

* Miri 并不完美，这其实仍然是未定义行为。
* 我们那套简化模型事实上过分简化了。

我会押注在第二个上，不过保险起见，我们还是写一个在我们那套简化的堆叠借用模型里绝对滴水不漏的版本：

```rust
use std::cell::UnsafeCell;

fn opaque_read(val: &i32) {
    println!("{}", val);
}

unsafe {
    let mut data = UnsafeCell::new(10);
    let mref1 = &mut data;
    // These two are swapped so the borrows are *definitely* totally stacked
    let sref2 = &*mref1;
    // Derive the ptr from the shared ref to be super safe!
    let ptr3 = sref2.get();             

    *ptr3 += 3;
    opaque_read(&*sref2.get());
    *sref2.get() += 2;
    *mref1.get() += 1;

    println!("{}", *data.get());
}
```

```text
cargo run
13
16

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
13
16
```

话说回来，我们最初那个实现*可能*其实是正确的，原因之一在于：如果你*认真*想想，就别名而言，`&UnsafeCell<T>`和`*mut T`真的没什么区别。你可以无限复制它，还能透过它做修改！

所以在某种意义上，我们不过是造了两个原始指针，然后像平常一样互换着使用它们。两者都是从那个可变引用派生出来的，这*是有点*可疑，所以也许第二个的创建仍然该把第一个从借用栈上弹掉；但这其实没必要，因为我们并没有*真的*去访问那个可变引用的内容，只是复制了它的地址。

像`let sref2 = &*mref1`这样的一行是个狡猾的东西。从*语法上*看，我们像是在解引用它，可解引用本身其实算不上一件*事*？想想`&my_tuple.0`：你其实并没有对`my_tuple`或者`.0`做任何事情，你只是用它们来指代内存中的某个位置，然后在前面加个`&`，意思是“别加载它，把地址记下来就行”。

`&*`也是一回事：`*`只是在说“嘿我们来谈谈这个指针所指向的位置”，而`&`只是在说“现在把那个地址记下来”。那当然就是原指针本来的那个值。只不过指针的类型变了，因为，呃，类型嘛！

话虽如此，如果你写的是`&**`，那你确实用第一个`*`加载了一个值！`*`真是个怪东西！

> **旁白：***Jonathan*，没人在乎你知道“左值”这个词。在 Rust 里我们管它们叫*位置*（place），这完全不一样，而且*酷*得多，好吧？




# 测试 Box

嘿，还记得我们为什么要开始这段极其漫长的题外话吗？不记得了？真奇怪。

嗯，是因为我们把 Box 和原始指针混着用了。Box *有点*像`&mut`，因为它主张对自己所指向的内存拥有独占所有权。我们来检验一下这个主张：

```rust ,ignore
unsafe {
    let mut data = Box::new(10);
    let ptr1 = (&mut *data) as *mut i32;

    *data += 10;
    *ptr1 += 1;

    // Should be 21
    println!("{}", data);
}
```

```text
cargo run
21

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run

error: Undefined Behavior: no item granting read access 
       to tag <1707> at alloc763 found in borrow stack.

 --> src\main.rs:7:5
  |
7 |     *ptr1 += 1;
  |     ^^^^^^^^^^ no item granting read access to tag <1707> 
  |                at alloc763 found in borrow stack.
  |
```

没错，miri 讨厌这个。我们来检查一下按正确顺序做事是不是就没问题：

```rust
unsafe {
    let mut data = Box::new(10);
    let ptr1 = (&mut *data) as *mut i32;

    *ptr1 += 1;
    *data += 10;

    // Should be 21
    println!("{}", data);
}
```

```text
cargo run
21

MIRIFLAGS="-Zmiri-tag-raw-pointers" cargo +nightly-2022-01-21 miri run
21
```

没错！

好啦各位，就这些了，我们终于把堆叠借用聊完、想完了！

……等等，那 Box 的这个问题我们到底要怎么解决？就是说，我们当然可以写这样的玩具程序，可我们得把 Box 存在某个地方，还要把原始指针攥在手里可能很长一段时间。那些东西肯定会搞混、失效的吧？

好问题！为了回答它，我们终于要回归我们真正的天职了：写他妈的链表。

等等，我又得写链表了？各位别急。讲点道理。等一下，我确信还有别的有趣问题值得我讨&mdash;